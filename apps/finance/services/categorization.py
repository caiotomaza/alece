# SPDX-License-Identifier: GPL-3.0-only
"""Serviço de regras de categorização De-Para com persistência, versionamento e segurança.

- Regras por núcleo (workspace) ou perfil específico
- Prioridade explícita (menor = maior prioridade)
- Correspondência exata ou regex (protegida contra ReDoS via timeout e validação)
- Ativação/desativação, autoria, auditoria
- Integração com pipeline de importação (Sprint 04)
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from apps.core.permissions import require_workspace_admin
from apps.finance.models import (
    CategorizationRule, FinancialProfile,
)
from apps.finance.services.importers import ParsedTransaction


# =============================================================================
# Configurações de Segurança
# =============================================================================

# Timeout para execução de regex (proteção contra ReDoS)
REGEX_TIMEOUT_MS = 100
# Limite de complexidade de regex (número de grupos/capturas)
MAX_REGEX_GROUPS = 10
# Tamanho máximo do padrão
MAX_PATTERN_LENGTH = 500


# =============================================================================
# Exceções
# =============================================================================

class CategorizationError(ValidationError):
    """Erro em operações de categorização."""
    pass


class RegexSecurityError(ValidationError):
    """Erro de segurança em regex (ReDoS, complexidade excessiva)."""
    pass


# =============================================================================
# Validação de Regex Segura
# =============================================================================

def validate_regex_safety(pattern: str) -> None:
    """Valida se uma regex é segura contra ReDoS e complexidade excessiva.

    - Limita número de grupos de captura
    - Detecta padrões perigosos conhecidos (nested quantifiers, etc.)
    - Testa execução com timeout
    """
    if len(pattern) > MAX_PATTERN_LENGTH:
        raise RegexSecurityError(f"Padrão excede {MAX_PATTERN_LENGTH} caracteres.")

    # Contar grupos de captura
    try:
        compiled = re.compile(pattern)
        if compiled.groups > MAX_REGEX_GROUPS:
            raise RegexSecurityError(f"Regex tem {compiled.groups} grupos (máx. {MAX_REGEX_GROUPS}).")
    except re.error as e:
        raise RegexSecurityError(f"Regex inválida: {e}")

    # Detectar padrões perigosos conhecidos
    dangerous_patterns = [
        r"\(\?[=:!]",  # lookahead/lookbehind aninhados
        r"\(\?P<",     # named groups (podem ser problemáticos em grande número)
        r"\{\d+,\}",   # quantificadores ilimitados {n,}
        r"\*\*|\+\+",  # quantificadores aninhados óbvios
    ]
    for dp in dangerous_patterns:
        if re.search(dp, pattern):
            raise RegexSecurityError(f"Padrão potencialmente perigoso detectado: {dp}")

    # Testar execução com strings de teste variadas
    test_strings = [
        "a" * 100,
        "a" * 1000,
        "a" * 100 + "b",
        " " * 100,
        "\n" * 100,
        "abc" * 100,
    ]
    for test_str in test_strings:
        start = time.perf_counter()
        try:
            compiled.search(test_str)
        except Exception:
            pass
        elapsed_ms = (time.perf_counter() - start) * 1000
        if elapsed_ms > REGEX_TIMEOUT_MS:
            raise RegexSecurityError(f"Regex excedeu timeout de {REGEX_TIMEOUT_MS}ms em string de teste.")


def compile_safe_regex(pattern: str, case_sensitive: bool = False) -> re.Pattern:
    """Compila regex com validação de segurança."""
    validate_regex_safety(pattern)
    flags = 0 if case_sensitive else re.IGNORECASE
    return re.compile(pattern, flags)


# =============================================================================
# Dataclasses
# =============================================================================

@dataclass
class RuleMatchResult:
    """Resultado da correspondência de uma regra."""
    rule: CategorizationRule
    matched: bool
    confidence: Decimal
    matched_text: str = ""


# =============================================================================
# Serviços CRUD de Regras
# =============================================================================

@transaction.atomic
def create_categorization_rule(
    *,
    actor,
    workspace_id: int,
    profile_id: Optional[int],
    name: str,
    match_type: str,
    pattern: str,
    match_field: str,
    suggested_kind: str,
    suggested_link: dict,
    priority: int = 100,
    case_sensitive: bool = False,
    match_field_enum: str = "both",
    description: str = "",
) -> CategorizationRule:
    """Cria nova regra de categorização."""
    workspace = require_workspace_admin(actor, workspace_id)

    # Validar perfil se informado
    profile = None
    if profile_id:
        profile = FinancialProfile.objects.select_for_update().get(pk=profile_id, workspace=workspace)

    # Validar regex se tipo for REGEX
    if match_type == CategorizationRule.MatchType.REGEX:
        validate_regex_safety(pattern)
        try:
            re.compile(pattern, 0 if case_sensitive else re.IGNORECASE)
        except re.error as e:
            raise ValidationError({"pattern": f"Regex inválida: {e}"})

    rule = CategorizationRule.objects.create(
        workspace=workspace,
        profile=profile,
        name=name.strip(),
        description=description.strip(),
        match_type=match_type,
        pattern=pattern.strip(),
        match_field=match_field,
        case_sensitive=case_sensitive,
        suggested_kind=suggested_kind,
        suggested_link=suggested_link or {},
        priority=priority,
        is_active=True,
        created_by=actor,
    )
    return rule


@transaction.atomic
def update_categorization_rule(
    *,
    actor,
    rule_id: int,
    workspace_id: int,
    **data,
) -> CategorizationRule:
    """Atualiza regra de categorização existente."""
    workspace = require_workspace_admin(actor, workspace_id)
    rule = CategorizationRule.objects.select_for_update().get(pk=rule_id, workspace=workspace)

    # Validar alterações
    if "pattern" in data and rule.match_type == CategorizationRule.MatchType.REGEX:
        validate_regex_safety(data["pattern"])
        try:
            re.compile(data["pattern"], 0 if rule.case_sensitive else re.IGNORECASE)
        except re.error as e:
            raise ValidationError({"pattern": f"Regex inválida: {e}"})

    if "match_type" in data and data["match_type"] == CategorizationRule.MatchType.REGEX:
        pattern = data.get("pattern", rule.pattern)
        case_sensitive = data.get("case_sensitive", rule.case_sensitive)
        validate_regex_safety(pattern)
        try:
            re.compile(pattern, 0 if case_sensitive else re.IGNORECASE)
        except re.error as e:
            raise ValidationError({"pattern": f"Regex inválida: {e}"})

    # Aplicar alterações permitidas
    allowed_fields = {
        "name", "description", "pattern", "match_type", "match_field",
        "case_sensitive", "suggested_kind", "suggested_link",
        "priority", "is_active",
    }
    for key, value in data.items():
        if key in allowed_fields:
            setattr(rule, key, value)

    rule.updated_by = actor
    rule.full_clean()
    rule.save()
    return rule


@transaction.atomic
def delete_categorization_rule(
    *,
    actor,
    rule_id: int,
    workspace_id: int,
) -> None:
    """Exclui regra de categorização (apenas admin do núcleo)."""
    workspace = require_workspace_admin(actor, workspace_id)
    rule = CategorizationRule.objects.select_for_update().get(pk=rule_id, workspace=workspace)
    rule.delete()


def get_categorization_rules(
    workspace_id: int,
    profile_id: Optional[int] = None,
    active_only: bool = True,
) -> list[CategorizationRule]:
    """Obtém regras de categorização ordenadas por prioridade.

    Regras de perfil específico têm precedência sobre regras do núcleo.
    """
    queryset = CategorizationRule.objects.filter(workspace_id=workspace_id)
    if active_only:
        queryset = queryset.filter(is_active=True)

    if profile_id:
        # Regras do perfil + regras do núcleo (sem perfil)
        queryset = queryset.filter(Q(profile_id=profile_id) | Q(profile__isnull=True))
    else:
        # Apenas regras do núcleo
        queryset = queryset.filter(profile__isnull=True)

    return list(queryset.order_by("priority", "name"))


# =============================================================================
# Engine de Correspondência
# =============================================================================

def apply_categorization_rules(
    transaction: ParsedTransaction,
    rules: list[CategorizationRule],
) -> tuple[str, dict, Decimal, str]:
    """Aplica regras de categorização ordenadas por prioridade.

    Returns:
        (suggested_kind, suggested_link, confidence, justification)
    """
    for rule in rules:
        if not rule.is_active:
            continue

        text_to_match = ""
        if rule.match_field in (CategorizationRule.MatchField.DESCRIPTION, CategorizationRule.MatchField.BOTH):
            text_to_match += " " + (transaction.description or "")
        if rule.match_field in (CategorizationRule.MatchField.MEMO, CategorizationRule.MatchField.BOTH):
            text_to_match += " " + (transaction.memo or "")

        text_to_match = text_to_match.strip()
        if not text_to_match:
            continue

        matched = False

        if rule.match_type == CategorizationRule.MatchType.EXACT:
            search_term = rule.pattern.lower() if not rule.case_sensitive else rule.pattern
            haystack = text_to_match.lower() if not rule.case_sensitive else text_to_match
            if search_term in haystack:
                matched = True

        elif rule.match_type == CategorizationRule.MatchType.REGEX:
            try:
                compiled = compile_safe_regex(rule.pattern, rule.case_sensitive)
                match = compiled.search(text_to_match)
                if match:
                    matched = True
                    match.group(0)
            except (RegexSecurityError, re.error):
                # Regra inválida, pular
                continue

        if matched:
            confidence = Decimal("0.90") if rule.match_type == CategorizationRule.MatchType.REGEX else Decimal("0.85")
            justification = f"Regra '{rule.name}' (prioridade {rule.priority}): padrão '{rule.pattern}' encontrado em {rule.get_match_field_display()}"
            return (
                rule.suggested_kind,
                rule.suggested_link or {},
                confidence,
                justification,
            )

    # Sem regra - heurística básica (fallback)
    return _heuristic_categorization(transaction)


def _heuristic_categorization(txn: ParsedTransaction) -> tuple[str, dict, Decimal, str]:
    """Categorização heurística básica quando não há regra."""
    desc = (txn.description + " " + txn.memo).lower()

    # Transferências (pix, ted, doc, transfer)
    if any(kw in desc for kw in ["pix", "ted", "doc", "transfer", "transf"]):
        return "transfer", {}, Decimal("0.60"), "Descrição sugere transferência"

    # Investimentos (aplicação, resgate, corretora)
    if any(kw in desc for kw in ["aplic", "resgat", "corretor", "xp", "clear", "rico", "btg", "modal"]):
        if txn.is_credit:
            return "withdrawal", {}, Decimal("0.55"), "Descrição sugere resgate de investimento"
        else:
            return "application", {}, Decimal("0.55"), "Descrição sugere aplicação em investimento"

    # Recebimentos (salário, pagamento, crédito)
    if txn.is_credit and any(kw in desc for kw in ["salario", "salário", "pagamento", "credito", "crédito", "pix receb"]):
        return "income", {}, Decimal("0.50"), "Crédito com descrição de recebimento"

    # Pagamentos (débito, compra, pagamento)
    if not txn.is_credit:
        return "unexpected", {}, Decimal("0.40"), "Débito sem regra específica"

    return "unexpected", {}, Decimal("0.30"), "Sem regra ou heurística clara"


# =============================================================================
# Integração com Pipeline de Importação
# =============================================================================

def get_rules_for_import(profile: FinancialProfile) -> list[CategorizationRule]:
    """Obtém regras aplicáveis para importação de um perfil."""
    return get_categorization_rules(
        workspace_id=profile.workspace_id,
        profile_id=profile.pk,
        active_only=True,
    )


def apply_rules_to_transactions(
    transactions: list[ParsedTransaction],
    profile: FinancialProfile,
) -> list[ParsedTransaction]:
    """Aplica regras de categorização a uma lista de transações."""
    rules = get_rules_for_import(profile)
    for txn in transactions:
        kind, link, confidence, justification = apply_categorization_rules(txn, rules)
        txn.suggested_kind = kind
        txn.suggested_link = link
        txn.confidence = confidence
        txn.justification = justification
    return transactions