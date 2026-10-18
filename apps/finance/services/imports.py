# SPDX-License-Identifier: GPL-3.0-only
"""Serviços de importação e conciliação bancária assistida.

Pipeline:
1. Upload → staging (ImportBatch + ImportRow)
2. Identificação instituição/conta
3. Normalização (datas, descrições, valores Decimal)
4. Associação a núcleo e perfil financeiro
5. Persistência em staging com hash SHA-256
6. Detecção conservadora de duplicidades
7. Reconciliação assistida (vínculo a lançamentos existentes)
8. Categorização por regras De-Para (persistidas, Sprint 05)
9. Prévia editável com confirmação humana obrigatória
10. Commit atômico com trilha de auditoria
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.core.permissions import require_module
from apps.finance.models import (
    BankAccount, FinancialProfile, ImportBatch, ImportRow,
    InvestmentPosition, MonthlyExpense, RecurringExpense,
    TransactionBatch, UnexpectedExpense,
)
from apps.finance.services.categorization import (
    get_rules_for_import, apply_rules_to_transactions,
)
from apps.finance.services.importers import (
    ParsedStatement, ParsedTransaction, detect_format, get_parser,
    ImportParseError, MAX_ROWS,
)


# =============================================================================
# Exceções
# =============================================================================

class ImportValidationError(ValidationError):
    """Erro de validação durante importação."""
    pass


class ImportCommitError(ValidationError):
    """Erro ao confirmar importação."""
    pass


# =============================================================================
# Detecção de Duplicidades
# =============================================================================

@dataclass
class DuplicateCheckResult:
    """Resultado da verificação de duplicidade."""
    is_duplicate: bool = False
    duplicate_type: str = ""  # "fitid", "contextual", "file_hash"
    existing_row: Optional[ImportRow] = None
    existing_batch: Optional[ImportBatch] = None
    confidence: Decimal = Decimal("0.00")
    details: str = ""


def check_duplicates(
    profile: FinancialProfile,
    account: Optional[BankAccount],
    statement: ParsedStatement,
    file_hash: str,
) -> list[DuplicateCheckResult]:
    """Verifica duplicidades de forma conservadora.
    
    Estratégias (em ordem de prioridade):
    1. FITID (identificador único do banco) - se presente
    2. Hash do arquivo (reimportação do mesmo arquivo)
    3. Comparação contextual: data + valor + descrição normalizada + instituição/conta
    
    NÃO presume que transações de mesmo valor e data sejam duplicadas.
    """
    results = []
    
    # 1. Verificar hash do arquivo (reimportação exata)
    existing_batch = ImportBatch.objects.filter(
        profile=profile, file_hash=file_hash
    ).first()
    
    if existing_batch:
        # Arquivo já importado - marcar todas como duplicadas por hash de arquivo
        for row in statement.transactions:
            results.append(DuplicateCheckResult(
                is_duplicate=True,
                duplicate_type="file_hash",
                existing_batch=existing_batch,
                confidence=Decimal("1.00"),
                details=f"Arquivo já importado em {existing_batch.created_at:%d/%m/%Y %H:%M} (batch #{existing_batch.pk})",
            ))
        return results
    
    # 2. Preparar consultas para FITID e contextual
    fitids = [txn.fitid for txn in statement.transactions if txn.fitid]
    
    # Buscar FITIDs existentes
    existing_fitids = set()
    if fitids:
        existing_fitids = set(
            ImportRow.objects.filter(
                batch__profile=profile, fitid__in=fitids
            ).values_list("fitid", flat=True)
        )
    
    # Buscar transações existentes no ledger para comparação contextual
    # Usamos um window de ±1 dia para data, valor exato, descrição similar
    ledger_txns = TransactionBatch.objects.filter(
        profile=profile,
        legs__account=account if account else Q(),
    ).select_related(
        "recurring_expense", "unexpected_expense", "investment", "monthly_expense"
    ).prefetch_related("legs__account")
    
    # Para cada transação do extrato
    for txn in statement.transactions:
        result = DuplicateCheckResult()
        
        # Verificar FITID
        if txn.fitid and txn.fitid in existing_fitids:
            existing_row = ImportRow.objects.filter(
                batch__profile=profile, fitid=txn.fitid
            ).select_related("batch").first()
            if existing_row:
                result.is_duplicate = True
                result.duplicate_type = "fitid"
                result.existing_row = existing_row
                result.existing_batch = existing_row.batch
                result.confidence = Decimal("0.95")
                result.details = f"FITID {txn.fitid} já importado (batch #{existing_row.batch_id})"
                results.append(result)
                continue
        
        # Verificar duplicidade contextual conservadora
        # Apenas se houver FITID E data/valor/descrição compatíveis
        if txn.occurred_on and txn.amount > 0:
            # Buscar no ledger
            ctx_matches = _find_contextual_matches(
                profile, account, txn, ledger_txns
            )
            if ctx_matches:
                # Verificar se já foi importado (tem ImportRow vinculado)
                imported_match = None
                for match in ctx_matches:
                    if hasattr(match, "import_rows") and match.import_rows.exists():
                        imported_match = match
                        break
                
                if imported_match:
                    result.is_duplicate = True
                    result.duplicate_type = "contextual"
                    result.existing_batch = imported_match
                    result.confidence = Decimal("0.70")
                    result.details = (
                        f"Possível duplicata contextual: {match.occurred_on:%d/%m/%Y} "
                        f"R$ {match.amount:.2f} - {match.note[:50]}"
                    )
                    results.append(result)
                    continue
        
        # Não é duplicata
        results.append(result)
    
    return results


def _find_contextual_matches(
    profile: FinancialProfile,
    account: Optional[BankAccount],
    txn: ParsedTransaction,
    ledger_txns,
) -> list[TransactionBatch]:
    """Busca correspondências contextuais no ledger.
    
    Critérios conservadores:
    - Data: ±1 dia
    - Valor: exato (centavos)
    - Descrição: similaridade alta (substring ou palavras-chave)
    - Conta: mesma conta (se informada)
    """
    if not txn.occurred_on:
        return []
    
    # Window de data
    from datetime import timedelta
    date_min = txn.occurred_on - timedelta(days=1)
    date_max = txn.occurred_on + timedelta(days=1)
    
    # Filtrar por data e valor
    candidates = ledger_txns.filter(
        occurred_on__range=(date_min, date_max),
        amount=txn.amount,
    )
    
    if account:
        candidates = candidates.filter(legs__account=account)
    
    # Filtrar por descrição (busca por palavras-chave)
    desc_words = set(re.findall(r"\w+", txn.description.lower()))
    desc_words = {w for w in desc_words if len(w) > 3}  # Palavras > 3 chars
    
    matches = []
    for batch in candidates:
        batch_desc = (batch.note or "").lower()
        batch_words = set(re.findall(r"\w+", batch_desc))
        
        # Verificar sobreposição significativa
        if desc_words and batch_words:
            overlap = desc_words & batch_words
            if len(overlap) >= 2 or (len(overlap) == 1 and len(desc_words) == 1):
                matches.append(batch)
    
    return matches


# =============================================================================
# Regras de Categorização (De-Para)
# =============================================================================

@dataclass
class CategorizationRule:
    """Regra de categorização configurável."""
    id: int
    name: str
    profile_id: int
    pattern: str  # Regex ou termo exato
    is_regex: bool
    match_field: str  # "description", "memo", "both"
    suggested_kind: str  # recurring, unexpected, application, withdrawal, transfer, income
    suggested_link: dict  # JSON com expense_id, investment_id, etc.
    # =============================================================================
# Serviço Principal de Importação
# =============================================================================

def stage_import(
    *,
    actor,
    profile_id: int,
    account_id: Optional[int],
    file_content: bytes,
    filename: str,
    format_hint: Optional[str] = None,
    parser_options: Optional[dict] = None,
) -> ImportBatch:
    """Cria lote de importação em staging.
    
    Validações:
    - Autorização (actor tem permissão edit no perfil e módulo accounts/movements)
    - Tamanho, tipo, codificação, estrutura do arquivo
    - Limites de processamento
    """
    # Autorização
    profile = require_module(actor, profile_id, "accounts", "edit")
    require_module(actor, profile_id, "movements", "edit")
    
    account = None
    if account_id:
        account = BankAccount.objects.filter(pk=account_id, profile=profile).first()
        if not account:
            raise ImportValidationError("Conta bancária não encontrada neste perfil.")
    
    # Detectar formato
    detected_format = format_hint or detect_format(filename, file_content)
    
    # Parse do arquivo
    parser = get_parser(detected_format, profile, account, **(parser_options or {}))
    statement = parser.parse(file_content, filename)
    
    if parser.errors:
        raise ImportParseError("; ".join(parser.errors))
    
    if not statement.transactions:
        raise ImportParseError("Nenhuma transação válida encontrada no arquivo.")
    
    if len(statement.transactions) > MAX_ROWS:
        raise ImportParseError(f"Arquivo excede o limite de {MAX_ROWS} transações.")
    
    # Hash do arquivo
    file_hash = hashlib.sha256(file_content).hexdigest()
    
    # Verificar duplicidade de arquivo
    existing = ImportBatch.objects.filter(profile=profile, file_hash=file_hash).first()
    if existing:
        raise ImportValidationError(
            f"Este arquivo já foi importado em {existing.created_at:%d/%m/%Y %H:%M} "
            f"(batch #{existing.pk})."
        )
    
    # Verificar duplicidades das transações
    duplicate_results = check_duplicates(profile, account, statement, file_hash)
    
    # Criar ImportBatch
    with transaction.atomic():
        batch = ImportBatch.objects.create(
            profile=profile,
            account=account,
            filename=filename,
            file_hash=file_hash,
            format=detected_format,
            parser_version=statement.parser_version,
            status=ImportBatch.Status.VALIDATED,
            total_rows=len(statement.transactions),
            valid_rows=0,  # Será atualizado
            duplicate_rows=0,
            error_rows=0,
            created_by=actor,
        )
        
        # Criar ImportRows
        valid_count = 0
        duplicate_count = 0
        error_count = 0
        
        for i, (txn, dup_result) in enumerate(zip(statement.transactions, duplicate_results)):
            # Aplicar categorização
            get_rules_for_import(profile)
            transactions = apply_rules_to_transactions([txn], profile)
            txn = transactions[0]
            kind = txn.suggested_kind
            link = txn.suggested_link
            confidence = txn.confidence
            justification = txn.justification
            
            # Sugerir vínculo com despesas/investimentos existentes
            suggested_link = _suggest_link(profile, account, txn, kind)
            if suggested_link:
                link = suggested_link
            
            status = ImportRow.Status.PENDING
            if dup_result.is_duplicate:
                status = ImportRow.Status.DUPLICATE
                duplicate_count += 1
            elif txn.occurred_on and txn.amount > 0:
                status = ImportRow.Status.SUGGESTED
                valid_count += 1
            else:
                status = ImportRow.Status.ERROR
                error_count += 1
            
            ImportRow.objects.create(
                batch=batch,
                row_number=i + 1,
                fitid=txn.fitid,
                occurred_on=txn.occurred_on or timezone.localdate(),
                posted_on=txn.posted_on,
                description=txn.description,
                memo=txn.memo,
                amount=txn.amount if not txn.is_credit else -txn.amount,  # Negativo = débito
                is_credit=txn.is_credit,
                raw_data=txn.raw_data,
                suggested_kind=kind,
                suggested_link=link,
                confidence=confidence,
                justification=justification,
                status=status,
            )
        
        # Atualizar contadores
        batch.valid_rows = valid_count
        batch.duplicate_rows = duplicate_count
        batch.error_rows = error_count
        batch.save(update_fields=["valid_rows", "duplicate_rows", "error_rows", "status"])
    
    return batch


def _suggest_link(
    profile: FinancialProfile,
    account: Optional[BankAccount],
    txn: ParsedTransaction,
    kind: str,
) -> dict:
    """Sugere vínculo com despesas/investimentos existentes."""
    link = {}
    
    if kind == "recurring":
        # Buscar despesa previsível por descrição similar e valor
        candidates = RecurringExpense.objects.filter(
            profile=profile, is_active=True, amount=txn.amount
        )
        for exp in candidates:
            if _descriptions_match(exp.name, txn.description):
                link = {"recurring_expense_id": exp.pk}
                break
    
    elif kind == "unexpected":
        # Buscar despesa imprevisível do mês
        if txn.occurred_on:
            txn.occurred_on.replace(day=1)
            candidates = UnexpectedExpense.objects.filter(
                profile=profile, recorded_on__month=txn.occurred_on.month,
                recorded_on__year=txn.occurred_on.year, amount=txn.amount
            )
            for exp in candidates:
                if _descriptions_match(exp.name, txn.description):
                    link = {"unexpected_expense_id": exp.pk}
                    break
    
    elif kind == "application":
        # Buscar posição de investimento
        candidates = InvestmentPosition.objects.filter(profile=profile, is_active=True)
        for inv in candidates:
            if _descriptions_match(inv.name, txn.description):
                link = {"investment_id": inv.pk}
                break
    
    elif kind == "withdrawal":
        candidates = InvestmentPosition.objects.filter(profile=profile, is_active=True)
        for inv in candidates:
            if _descriptions_match(inv.name, txn.description):
                link = {"investment_id": inv.pk}
                break
    
    return link


def _descriptions_match(desc1: str, desc2: str) -> bool:
    """Verifica se duas descrições são similares o suficiente."""
    words1 = set(re.findall(r"\w+", desc1.lower()))
    words2 = set(re.findall(r"\w+", desc2.lower()))
    words1 = {w for w in words1 if len(w) > 3}
    words2 = {w for w in words2 if len(w) > 3}
    
    if not words1 or not words2:
        return False
    
    overlap = words1 & words2
    return len(overlap) >= 2 or (len(overlap) == 1 and len(words1) <= 2 and len(words2) <= 2)


# =============================================================================
# Reconciliação Assistida
# =============================================================================

@dataclass
class ReconciliationSuggestion:
    """Sugestão de reconciliação para uma linha de importação."""
    import_row: ImportRow
    action: str  # "link_existing", "create_new", "ignore", "partial_payment", "split"
    target_batch: Optional[TransactionBatch] = None
    target_expense: Optional[MonthlyExpense] = None
    target_investment: Optional[InvestmentPosition] = None
    confidence: Decimal = Decimal("0.00")
    justification: str = ""
    warnings: list[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


def generate_reconciliation_suggestions(batch: ImportBatch) -> list[ReconciliationSuggestion]:
    """Gera sugestões de reconciliação para todas as linhas do lote."""
    suggestions = []
    
    for row in batch.rows.filter(
        status__in=[ImportRow.Status.SUGGESTED, ImportRow.Status.DUPLICATE]
    ).select_related("batch__profile", "batch__account"):
        
        suggestion = _analyze_row_for_reconciliation(row)
        suggestions.append(suggestion)
    
    return suggestions


def _analyze_row_for_reconciliation(row: ImportRow) -> ReconciliationSuggestion:
    """Analisa uma linha e gera sugestão de reconciliação."""
    profile = row.batch.profile
    account = row.batch.account
    
    # Se já tem linked_batch, é duplicata confirmada
    if row.linked_batch:
        return ReconciliationSuggestion(
            import_row=row,
            action="ignore",
            confidence=Decimal("1.00"),
            justification="Já vinculada a movimentação existente",
            warnings=["Esta transação já foi importada e vinculada anteriormente"],
        )
    
    # Se é duplicata por FITID/hash, sugerir ignorar
    if row.status == ImportRow.Status.DUPLICATE:
        return ReconciliationSuggestion(
            import_row=row,
            action="ignore",
            confidence=Decimal("0.90"),
            justification="Duplicata detectada (FITID ou hash de arquivo)",
            warnings=["Transação idêntica já existe no sistema"],
        )
    
    # Buscar movimentações existentes compatíveis
    existing_movements = _find_reconcilable_movements(profile, account, row)
    
    if existing_movements:
        # Verificar se é pagamento parcial
        best_match = existing_movements[0]
        if best_match.kind in ("recurring", "unexpected"):
            monthly_expense = best_match.monthly_expense or (
                best_match.unexpected_expense and _get_monthly_for_unexpected(best_match.unexpected_expense)
            )
            if monthly_expense:
                paid = _get_paid_amount(monthly_expense)
                due = monthly_expense.amount
                remaining = due - paid
                
                if row.amount > 0 and row.amount < remaining:
                    return ReconciliationSuggestion(
                        import_row=row,
                        action="partial_payment",
                        target_batch=best_match,
                        target_expense=monthly_expense,
                        confidence=Decimal("0.80"),
                        justification=(
                            f"Pagamento parcial de {monthly_expense.recurring_expense.name if hasattr(monthly_expense, 'recurring_expense') else 'despesa'}: "
                            f"R$ {row.amount:.2f} de R$ {remaining:.2f} restantes"
                        ),
                        warnings=[f"Valor inferior ao devido (R$ {remaining:.2f})"]
                    )
                elif row.amount >= remaining:
                    return ReconciliationSuggestion(
                        import_row=row,
                        action="link_existing",
                        target_batch=best_match,
                        target_expense=monthly_expense,
                        confidence=Decimal("0.85"),
                        justification="Quitação total de despesa existente"
                    )
    
    # Verificar se é aplicação/resgate em investimento
    if row.suggested_kind in ("application", "withdrawal") and row.suggested_link.get("investment_id"):
        inv_id = row.suggested_link["investment_id"]
        investment = InvestmentPosition.objects.filter(pk=inv_id, profile=profile).first()
        if investment:
            return ReconciliationSuggestion(
                import_row=row,
                action="link_existing",
                target_investment=investment,
                confidence=row.confidence,
                justification=f"{'Aplicação' if row.suggested_kind == 'application' else 'Resgate'} em {investment.name}"
            )
    
    # Verificar transferência entre contas do mesmo perfil
    if row.suggested_kind == "transfer":
        return ReconciliationSuggestion(
            import_row=row,
            action="create_new",
            confidence=Decimal("0.50"),
            justification="Transferência entre contas próprias (nova movimentação)",
            warnings=["Confirmar contas de origem e destino"]
        )
    
    # Nova despesa imprevisível
    if row.suggested_kind == "unexpected":
        return ReconciliationSuggestion(
            import_row=row,
            action="create_new",
            confidence=row.confidence,
            justification="Nova despesa imprevisível",
            warnings=["Será criada despesa imprevisível e pagamento associado"]
        )
    
    # Recebimento
    if row.suggested_kind == "income":
        return ReconciliationSuggestion(
            import_row=row,
            action="create_new",
            confidence=row.confidence,
            justification="Novo recebimento",
            warnings=["Recebimentos não vinculam a despesas automaticamente"]
        )
    
    # Default: criar novo
    return ReconciliationSuggestion(
        import_row=row,
        action="create_new",
        confidence=row.confidence,
        justification=row.justification or "Nova movimentação sem regra específica",
        warnings=["Revisar categorização e vínculos antes de confirmar"]
    )


def _find_reconcilable_movements(
    profile: FinancialProfile,
    account: Optional[BankAccount],
    row: ImportRow,
) -> list[TransactionBatch]:
    """Busca movimentações existentes que podem ser reconciliadas."""
    if not row.occurred_on:
        return []
    
    from datetime import timedelta
    date_min = row.occurred_on - timedelta(days=1)
    date_max = row.occurred_on + timedelta(days=1)
    
    # Valor absoluto para comparação
    abs_amount = abs(row.amount)
    
    query = TransactionBatch.objects.filter(
        profile=profile,
        occurred_on__range=(date_min, date_max),
        amount=abs_amount,
        reversal__isnull=True,  # Não estornados
    ).select_related(
        "monthly_expense__recurring_expense",
        "unexpected_expense",
        "investment",
    ).prefetch_related("legs__account")
    
    if account:
        query = query.filter(legs__account=account)
    
    return list(query[:10])  # Limitar resultados


def _get_monthly_for_unexpected(expense: UnexpectedExpense) -> Optional[MonthlyExpense]:
    """Obtém ou cria MonthlyExpense para despesa imprevisível."""
    # Despesas imprevisíveis não têm MonthlyExpense, usamos a própria
    return None


def _get_paid_amount(monthly_expense: MonthlyExpense) -> Decimal:
    """Calcula valor já pago de um MonthlyExpense."""
    from apps.finance.services.ledger import _active_paid
    from apps.finance.models import TransactionBatch
    paid = _active_paid(TransactionBatch.objects.filter(
        monthly_expense=monthly_expense, kind="recurring",
    ))
    return paid


# =============================================================================
# Commit da Importação (Confirmação Humana Obrigatória)
# =============================================================================

def commit_import(
    *,
    actor,
    batch_id: int,
    row_decisions: list[dict],
    idempotency_key: str,
) -> ImportBatch:
    """Confirma importação após revisão humana.
    
    row_decisions: lista de dicts com:
    - row_id: int
    - action: "link_existing" | "create_new" | "ignore" | "partial_payment" | "split"
    - target_batch_id: int (opcional)
    - target_expense_id: int (opcional)
    - target_investment_id: int (opcional)
    - splits: dict (opcional, para pagamento multi-conta)
    - adjusted_amount: Decimal (opcional)
    - adjusted_description: str (opcional)
    - adjusted_kind: str (opcional)
    - competence_month: str (YYYY-MM, opcional)
    """
    # Validações
    batch = ImportBatch.objects.select_related("profile", "account").get(pk=batch_id)
    profile = require_module(actor, batch.profile_id, "accounts", "edit")
    require_module(actor, batch.profile_id, "movements", "edit")
    
    if batch.status == ImportBatch.Status.COMMITTED:
        raise ImportCommitError("Este lote já foi confirmado.")
    
    if batch.status == ImportBatch.Status.FAILED:
        raise ImportCommitError("Este lote falhou na validação.")
    
    # Validar idempotência
    if ImportBatch.objects.filter(
        profile=profile, idempotency_key=idempotency_key
    ).exclude(pk=batch_id).exists():
        raise ImportCommitError("Chave idempotente já utilizada.")
    
    # Processar cada decisão
    created_batches = []
    
    with transaction.atomic():
        for decision in row_decisions:
            row = ImportRow.objects.select_related("batch").get(
                pk=decision["row_id"], batch=batch
            )
            
            if row.status == ImportRow.Status.COMMITTED:
                continue  # Já processado
            
            if decision["action"] == "ignore":
                row.status = ImportRow.Status.IGNORED
                row.decided_by = actor
                row.decided_at = timezone.now()
                row.save(update_fields=["status", "decided_by", "decided_at"])
                continue
            
            # Preparar parâmetros
            amount = decision.get("adjusted_amount", abs(row.amount))
            description = decision.get("adjusted_description", row.description)
            kind = decision.get("adjusted_kind", row.suggested_kind)
            competence = decision.get("competence_month")
            if competence:
                competence = date.fromisoformat(competence + "-01")
            
            # Determinar contas para split
            splits = decision.get("splits")
            if not splits:
                if batch.account:
                    splits = {batch.account.pk: amount}
                else:
                    raise ImportCommitError(f"Linha {row.row_number}: conta de destino obrigatória.")
            
            # Executar ação
            if decision["action"] == "link_existing":
                target_batch_id = decision.get("target_batch_id")
                if target_batch_id:
                    target_batch = TransactionBatch.objects.get(pk=target_batch_id)
                    row.linked_batch = target_batch
                    row.status = ImportRow.Status.COMMITTED
                    row.decided_by = actor
                    row.decided_at = timezone.now()
                    row.save(update_fields=["linked_batch", "status", "decided_by", "decided_at"])
                    continue
            
            elif decision["action"] == "create_new":
                new_batch = _create_transaction_from_row(
                    actor=actor,
                    profile=profile,
                    row=row,
                    kind=kind,
                    amount=amount,
                    description=description,
                    splits=splits,
                    competence_month=competence,
                    idempotency_key=f"{idempotency_key}:{row.row_number}",
                )
                row.linked_batch = new_batch
                row.status = ImportRow.Status.COMMITTED
                row.decided_by = actor
                row.decided_at = timezone.now()
                row.save(update_fields=["linked_batch", "status", "decided_by", "decided_at"])
                created_batches.append(new_batch)
            
            elif decision["action"] == "partial_payment":
                target_expense_id = decision.get("target_expense_id")
                if target_expense_id:
                    monthly_expense = MonthlyExpense.objects.get(pk=target_expense_id)
                    new_batch = _create_transaction_from_row(
                        actor=actor,
                        profile=profile,
                        row=row,
                        kind="recurring",
                        amount=amount,
                        description=description,
                        splits=splits,
                        competence_month=monthly_expense.competence_month,
                        idempotency_key=f"{idempotency_key}:{row.row_number}",
                        recurring_expense_id=monthly_expense.recurring_expense_id,
                        monthly_expense=monthly_expense,
                    )
                    row.linked_batch = new_batch
                    row.status = ImportRow.Status.COMMITTED
                    row.decided_by = actor
                    row.decided_at = timezone.now()
                    row.save(update_fields=["linked_batch", "status", "decided_by", "decided_at"])
                    created_batches.append(new_batch)
        
        # Atualizar status do batch
        batch.status = ImportBatch.Status.COMMITTED
        batch.committed_at = timezone.now()
        batch.idempotency_key = idempotency_key
        batch.save(update_fields=["status", "committed_at", "idempotency_key"])
    
    return batch


def _create_transaction_from_row(
    *,
    actor,
    profile: FinancialProfile,
    row: ImportRow,
    kind: str,
    amount: Decimal,
    description: str,
    splits: dict[int, Decimal],
    competence_month: Optional[date],
    idempotency_key: str,
    recurring_expense_id: Optional[int] = None,
    monthly_expense: Optional[MonthlyExpense] = None,
) -> TransactionBatch:
    """Cria TransactionBatch a partir de decisão de importação."""
    from apps.finance.services.ledger import confirm_outflow, transfer, withdraw_investment
    
    # Validar splits
    total_splits = sum(splits.values(), Decimal("0.00"))
    if total_splits != amount:
        raise ImportCommitError(
            f"Soma dos splits (R$ {total_splits:.2f}) difere do valor (R$ {amount:.2f})"
        )
    
    # Executar serviço apropriado
    if kind == "recurring":
        if not recurring_expense_id and monthly_expense:
            recurring_expense_id = monthly_expense.recurring_expense_id
        return confirm_outflow(
            actor=actor,
            profile_id=profile.pk,
            kind="recurring",
            splits=splits,
            idempotency_key=idempotency_key,
            note=description,
            competence_month=competence_month,
            recurring_expense_id=recurring_expense_id,
        )
    
    elif kind == "unexpected":
        # Criar ou buscar UnexpectedExpense
        unexpected_expense = None
        if row.suggested_link.get("unexpected_expense_id"):
            unexpected_expense = UnexpectedExpense.objects.get(
                pk=row.suggested_link["unexpected_expense_id"], profile=profile
            )
        else:
            unexpected_expense = UnexpectedExpense.objects.create(
                profile=profile,
                name=description,
                amount=amount,
                recorded_on=row.occurred_on or timezone.localdate(),
            )
        
        return confirm_outflow(
            actor=actor,
            profile_id=profile.pk,
            kind="unexpected",
            splits=splits,
            idempotency_key=idempotency_key,
            note=description,
            competence_month=row.occurred_on.replace(day=1) if row.occurred_on else None,
            unexpected_expense_id=unexpected_expense.pk,
        )
    
    elif kind == "application":
        investment_id = row.suggested_link.get("investment_id")
        if not investment_id:
            raise ImportCommitError("Aplicação requer investimento de destino.")
        
        return confirm_outflow(
            actor=actor,
            profile_id=profile.pk,
            kind="application",
            splits=splits,
            idempotency_key=idempotency_key,
            note=description,
            competence_month=competence_month,
            investment_id=investment_id,
        )
    
    elif kind == "withdrawal":
        investment_id = row.suggested_link.get("investment_id")
        if not investment_id:
            raise ImportCommitError("Resgate requer investimento de origem.")
        
        # Para resgate, splits é a conta de destino
        destination_id = list(splits.keys())[0]
        
        return withdraw_investment(
            actor=actor,
            profile_id=profile.pk,
            investment_id=investment_id,
            destination_id=destination_id,
            amount=amount,
            idempotency_key=idempotency_key,
            note=description,
        )
    
    elif kind == "transfer":
        # Transferência requer origem e destino
        if len(splits) != 2:
            raise ImportCommitError("Transferência requer exatamente 2 contas (origem e destino).")
        
        accounts = list(splits.items())
        # Determinar origem (débito) e destino (crédito)
        # A conta com valor negativo é origem
        source_id = accounts[0][0]
        dest_id = accounts[1][0]
        source_amount = accounts[0][1]
        
        # Se source_amount for negativo, inverter
        if source_amount < 0:
            source_id, dest_id = dest_id, source_id
            amount = abs(source_amount)
        
        return transfer(
            actor=actor,
            profile_id=profile.pk,
            source_id=source_id,
            destination_id=dest_id,
            amount=amount,
            idempotency_key=idempotency_key,
            note=description,
        )
    
    elif kind == "income":
        # Recebimento - crédito em conta
        from apps.finance.services.ledger import confirm_outflow
        return confirm_outflow(
            actor=actor,
            profile_id=profile.pk,
            kind="income",
            splits=splits,
            idempotency_key=idempotency_key,
            note=description,
            competence_month=competence_month,
        )
    
    else:
        raise ImportCommitError(f"Tipo de movimentação não suportado: {kind}")


# =============================================================================
# Dry-run e Relatório
# =============================================================================

@dataclass
class ImportReport:
    """Relatório detalhado de importação."""
    batch: ImportBatch
    total_rows: int
    committed: int
    linked_existing: int
    ignored: int
    errors: int
    duplicates: int
    created_batches: list[TransactionBatch]
    warnings: list[str]
    summary: str


def generate_import_report(batch: ImportBatch) -> ImportReport:
    """Gera relatório detalhado pós-importação."""
    rows = batch.rows.all()
    
    committed = rows.filter(status=ImportRow.Status.COMMITTED).count()
    linked = rows.filter(status=ImportRow.Status.COMMITTED, linked_batch__isnull=False).exclude(
        linked_batch__kind="income"
    ).count()
    ignored = rows.filter(status=ImportRow.Status.IGNORED).count()
    errors = rows.filter(status=ImportRow.Status.ERROR).count()
    duplicates = rows.filter(status=ImportRow.Status.DUPLICATE).count()
    
    created_batches = TransactionBatch.objects.filter(
        import_rows__batch=batch
    ).distinct()
    
    warnings = []
    if duplicates > 0:
        warnings.append(f"{duplicates} transação(ões) duplicada(s) detectada(s) e ignorada(s)")
    if errors > 0:
        warnings.append(f"{errors} transação(ões) com erro(s) de validação")
    
    summary = (
        f"Importação de {batch.filename}: "
        f"{committed} confirmada(s), {linked} vinculada(s) a existentes, "
        f"{ignored} ignorada(s), {duplicates} duplicada(s), {errors} erro(s)."
    )
    
    return ImportReport(
        batch=batch,
        total_rows=batch.total_rows,
        committed=committed,
        linked_existing=linked,
        ignored=ignored,
        errors=errors,
        duplicates=duplicates,
        created_batches=list(created_batches),
        warnings=warnings,
        summary=summary,
    )


def dry_run_import(
    *,
    actor,
    profile_id: int,
    account_id: Optional[int],
    file_content: bytes,
    filename: str,
    format_hint: Optional[str] = None,
    parser_options: Optional[dict] = None,
) -> tuple[ImportBatch, list[ReconciliationSuggestion]]:
    """Executa importação em modo dry-run (sem gravar no banco)."""
    # Autorização (apenas view)
    profile = require_module(actor, profile_id, "accounts", "view")
    require_module(actor, profile_id, "movements", "view")
    
    account = None
    if account_id:
        account = BankAccount.objects.filter(pk=account_id, profile=profile).first()
    
    # Detectar e parsear
    detected_format = format_hint or detect_format(filename, file_content)
    parser = get_parser(detected_format, profile, account, **(parser_options or {}))
    statement = parser.parse(file_content, filename)
    
    if parser.errors:
        raise ImportParseError("; ".join(parser.errors))
    
    file_hash = hashlib.sha256(file_content).hexdigest()
    duplicate_results = check_duplicates(profile, account, statement, file_hash)
    
    # Simular criação de batch (sem salvar)
    mock_batch = ImportBatch(
        profile=profile,
        account=account,
        filename=filename,
        file_hash=file_hash,
        format=detected_format,
        parser_version=statement.parser_version,
        status=ImportBatch.Status.VALIDATED,
        total_rows=len(statement.transactions),
    )
    
    # Criar rows em memória para sugestões
    mock_rows = []
    for i, (txn, dup_result) in enumerate(zip(statement.transactions, duplicate_results)):
        transactions = apply_rules_to_transactions([txn], profile)
        txn = transactions[0]
        kind = txn.suggested_kind
        link = txn.suggested_link
        confidence = txn.confidence
        justification = txn.justification
        suggested_link = _suggest_link(profile, account, txn, kind)
        if suggested_link:
            link = suggested_link
        
        status = ImportRow.Status.PENDING
        if dup_result.is_duplicate:
            status = ImportRow.Status.DUPLICATE
        elif txn.occurred_on and txn.amount > 0:
            status = ImportRow.Status.SUGGESTED
        else:
            status = ImportRow.Status.ERROR
        
        mock_row = ImportRow(
            batch=mock_batch,
            row_number=i + 1,
            fitid=txn.fitid,
            occurred_on=txn.occurred_on or timezone.localdate(),
            posted_on=txn.posted_on,
            description=txn.description,
            memo=txn.memo,
            amount=txn.amount if not txn.is_credit else -txn.amount,
            is_credit=txn.is_credit,
            raw_data=txn.raw_data,
            suggested_kind=kind,
            suggested_link=link,
            confidence=confidence,
            justification=justification,
            status=status,
        )
        mock_rows.append(mock_row)
    
    # Gerar sugestões
    suggestions = []
    for row in mock_rows:
        suggestion = _analyze_row_for_reconciliation(row)
        suggestions.append(suggestion)
    
    return mock_batch, suggestions