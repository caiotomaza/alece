# SPDX-License-Identifier: GPL-3.0-only
"""Views para importação e conciliação bancária assistida."""
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from apps.core.permissions import require_module, user_can_module
from apps.finance.models import (
    BankAccount, FinancialProfile, ImportBatch, ImportRow, TransactionBatch,
)
from apps.finance.services.imports import (
    commit_import, generate_import_report,
    generate_reconciliation_suggestions, stage_import,
    ImportParseError, ImportValidationError, ImportCommitError,
)


# =============================================================================
# Helpers
# =============================================================================

def _import_return_url(profile, tab="import"):
    return reverse("finance:import-list", args=[profile.workspace_id]) + f"?tab={tab}"


# =============================================================================
# Listagem de Importações
# =============================================================================

@login_required
@require_http_methods(["GET"])
def import_list(request, workspace_id):
    """Lista lotes de importação do workspace."""
    profile = require_module(request.user, workspace_id, "accounts", "view")
    require_module(request.user, workspace_id, "movements", "view")
    
    batches = ImportBatch.objects.filter(
        profile__workspace_id=workspace_id
    ).select_related("profile", "account", "created_by").order_by("-created_at")
    
    # Filtrar por perfil se selecionado
    profile_id = request.GET.get("profile")
    if profile_id:
        batches = batches.filter(profile_id=profile_id)
    
    profiles = FinancialProfile.objects.filter(
        workspace_id=workspace_id, is_archived=False
    )
    
    return render(request, "finance/import_list.html", {
        "workspace": profile.workspace,
        "profile": profile,
        "batches": batches,
        "profiles": profiles,
        "selected_profile": int(profile_id) if profile_id else None,
        "can_import": user_can_module(request.user, profile.pk, "accounts", "edit") and
                      user_can_module(request.user, profile.pk, "movements", "edit"),
    })


# =============================================================================
# Upload e Staging
# =============================================================================

@login_required
@require_http_methods(["GET", "POST"])
def import_upload(request, profile_id):
    """Upload de arquivo e criação de lote em staging."""
    profile = require_module(request.user, profile_id, "accounts", "edit")
    require_module(request.user, profile_id, "movements", "edit")
    
    accounts = BankAccount.objects.filter(profile=profile, is_archived=False)
    
    if request.method == "POST":
        uploaded_file = request.FILES.get("file")
        account_id = request.POST.get("account_id")
        
        if not uploaded_file:
            messages.error(request, "Selecione um arquivo para importar.")
        else:
            try:
                # Ler conteúdo do arquivo
                file_content = uploaded_file.read()
                
                # Opções do parser
                parser_options = {}
                if request.POST.get("encoding"):
                    parser_options["encoding"] = request.POST["encoding"]
                if request.POST.get("delimiter"):
                    parser_options["delimiter"] = request.POST["delimiter"]
                if request.POST.get("has_header") == "false":
                    parser_options["has_header"] = False
                if request.POST.get("credit_debit_columns") == "true":
                    parser_options["credit_debit_columns"] = True
                
                # Stage import
                batch = stage_import(
                    actor=request.user,
                    profile_id=profile.pk,
                    account_id=int(account_id) if account_id else None,
                    file_content=file_content,
                    filename=uploaded_file.name,
                    format_hint=request.POST.get("format") or None,
                    parser_options=parser_options,
                )
                
                messages.success(
                    request,
                    f"Arquivo importado com sucesso! {batch.valid_rows} transações válidas, "
                    f"{batch.duplicate_rows} duplicatas, {batch.error_rows} erros."
                )
                return redirect("finance:import-preview", profile_id=profile.pk, batch_id=batch.pk)
                
            except ImportParseError as e:
                messages.error(request, f"Erro ao processar arquivo: {str(e)}")
            except ImportValidationError as e:
                messages.error(request, str(e))
            except ValidationError as e:
                messages.error(request, "; ".join(e.messages))
            except Exception as e:
                messages.error(request, f"Erro inesperado: {str(e)}")
    
    return render(request, "finance/import_upload.html", {
        "workspace": profile.workspace,
        "profile": profile,
        "accounts": accounts,
        "cancel_url": _import_return_url(profile),
    })


# =============================================================================
# Prévia Editável (Dry-run / Preview)
# =============================================================================

@login_required
@require_http_methods(["GET"])
def import_preview(request, profile_id, batch_id):
    """Prévia editável do lote de importação com sugestões de reconciliação."""
    profile = require_module(request.user, profile_id, "accounts", "view")
    require_module(request.user, profile_id, "movements", "view")
    
    batch = get_object_or_404(
        ImportBatch.objects.select_related("profile", "account", "created_by"),
        pk=batch_id, profile=profile
    )
    
    # Gerar sugestões de reconciliação
    suggestions = generate_reconciliation_suggestions(batch)
    
    # Agrupar por status/action
    rows_data = []
    for suggestion in suggestions:
        row = suggestion.import_row
        rows_data.append({
            "row": row,
            "suggestion": suggestion,
            "can_edit": user_can_module(request.user, profile_id, "movements", "edit"),
        })
    
    # Estatísticas
    stats = {
        "total": batch.total_rows,
        "valid": batch.valid_rows,
        "duplicates": batch.duplicate_rows,
        "errors": batch.error_rows,
        "suggested_link": sum(1 for s in suggestions if s.action == "link_existing"),
        "suggested_new": sum(1 for s in suggestions if s.action == "create_new"),
        "suggested_partial": sum(1 for s in suggestions if s.action == "partial_payment"),
        "ignored": sum(1 for s in suggestions if s.action == "ignore"),
    }
    
    return render(request, "finance/import_preview.html", {
        "workspace": profile.workspace,
        "profile": profile,
        "batch": batch,
        "rows_data": rows_data,
        "stats": stats,
        "can_commit": (
            user_can_module(request.user, profile_id, "accounts", "edit") and
            user_can_module(request.user, profile_id, "movements", "edit") and
            batch.status in [ImportBatch.Status.VALIDATED, ImportBatch.Status.REVIEWED]
        ),
        "can_edit_rows": user_can_module(request.user, profile_id, "movements", "edit"),
        "cancel_url": _import_return_url(profile),
        "commit_url": reverse("finance:import-commit", args=[profile.pk, batch.pk]),
        "dry_run_url": reverse("finance:import-dry-run", args=[profile.pk, batch.pk]),
    })


@login_required
@require_http_methods(["POST"])
def import_dry_run(request, profile_id, batch_id):
    """Executa dry-run do commit (simulação sem gravar)."""
    profile = require_module(request.user, profile_id, "accounts", "view")
    require_module(request.user, profile_id, "movements", "view")
    
    batch = get_object_or_404(ImportBatch, pk=batch_id, profile=profile)
    
    # Coletar decisões do formulário
    row_decisions = []
    for key, value in request.POST.items():
        if key.startswith("row_") and key.endswith("_action"):
            row_id = int(key.split("_")[1])
            action = value
            
            decision = {"row_id": row_id, "action": action}
            
            # Parâmetros adicionais
            for param in ["target_batch_id", "target_expense_id", "target_investment_id",
                          "adjusted_amount", "adjusted_description", "adjusted_kind",
                          "competence_month"]:
                param_key = f"row_{row_id}_{param}"
                if param_key in request.POST:
                    decision[param] = request.POST[param_key]
            
            # Splits (multi-conta)
            splits = {}
            for split_key, split_value in request.POST.items():
                if split_key.startswith(f"row_{row_id}_split_") and split_value:
                    account_pk = int(split_key.split("_")[-1])
                    splits[account_pk] = Decimal(split_value)
            if splits:
                decision["splits"] = splits
            
            row_decisions.append(decision)
    
    if not row_decisions:
        return JsonResponse({"error": "Nenhuma decisão informada."}, status=400)
    
    # Simular commit (dry-run)
    try:
        # Validar decisões sem executar
        validation_errors = []
        for decision in row_decisions:
            row = ImportRow.objects.get(pk=decision["row_id"], batch=batch)
            error = _validate_decision(profile, batch.account, row, decision)
            if error:
                validation_errors.append(f"Linha {row.row_number}: {error}")
        
        if validation_errors:
            return JsonResponse({
                "valid": False,
                "errors": validation_errors,
            })
        
        return JsonResponse({
            "valid": True,
            "message": "Dry-run válido. Nenhuma alteração foi feita.",
            "would_create": sum(1 for d in row_decisions if d["action"] == "create_new"),
            "would_link": sum(1 for d in row_decisions if d["action"] == "link_existing"),
            "would_ignore": sum(1 for d in row_decisions if d["action"] == "ignore"),
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


def _validate_decision(profile, account, row, decision) -> Optional[str]:
    """Valida uma decisão de importação."""
    action = decision["action"]
    
    if action == "ignore":
        return None
    
    if action == "link_existing":
        target_batch_id = decision.get("target_batch_id")
        if not target_batch_id:
            return "Vínculo requer movimentação alvo."
        try:
            TransactionBatch.objects.get(pk=target_batch_id, profile=profile)
        except TransactionBatch.DoesNotExist:
            return "Movimentação alvo não encontrada."
        return None
    
    if action in ("create_new", "partial_payment"):
        amount = decision.get("adjusted_amount")
        if not amount:
            return "Valor ajustado obrigatório."
        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                return "Valor deve ser positivo."
        except (ValueError, ArithmeticError, TypeError):
            return "Valor inválido."
        
        splits = decision.get("splits")
        if not splits:
            if not account:
                return "Conta de destino obrigatória."
        else:
            total = sum(splits.values(), Decimal("0.00"))
            if total != amount:
                return f"Soma dos splits (R$ {total:.2f}) difere do valor (R$ {amount:.2f})."
        
        return None
    
    return "Ação inválida."


# =============================================================================
# Commit (Confirmação Humana Obrigatória)
# =============================================================================

@login_required
@require_POST
def import_commit(request, profile_id, batch_id):
    """Confirma importação após revisão humana obrigatória."""
    profile = require_module(request.user, profile_id, "accounts", "edit")
    require_module(request.user, profile_id, "movements", "edit")
    
    batch = get_object_or_404(ImportBatch, pk=batch_id, profile=profile)
    
    if batch.status == ImportBatch.Status.COMMITTED:
        messages.error(request, "Este lote já foi confirmado.")
        return redirect("finance:import-report", profile_id=profile.pk, batch_id=batch.pk)
    
    # Coletar decisões
    row_decisions = []
    for key, value in request.POST.items():
        if key.startswith("row_") and key.endswith("_action"):
            row_id = int(key.split("_")[1])
            action = value
            
            decision = {"row_id": row_id, "action": action}
            
            for param in ["target_batch_id", "target_expense_id", "target_investment_id",
                          "adjusted_amount", "adjusted_description", "adjusted_kind",
                          "competence_month"]:
                param_key = f"row_{row_id}_{param}"
                if param_key in request.POST:
                    decision[param] = request.POST[param_key]
            
            splits = {}
            for split_key, split_value in request.POST.items():
                if split_key.startswith(f"row_{row_id}_split_") and split_value:
                    account_pk = int(split_key.split("_")[-1])
                    splits[account_pk] = Decimal(split_value)
            if splits:
                decision["splits"] = splits
            
            row_decisions.append(decision)
    
    if not row_decisions:
        messages.error(request, "Nenhuma decisão informada.")
        return redirect("finance:import-preview", profile_id=profile.pk, batch_id=batch.pk)
    
    # Chave idempotente
    idempotency_key = request.POST.get("idempotency_key") or uuid4().hex
    
    try:
        batch = commit_import(
            actor=request.user,
            batch_id=batch.pk,
            row_decisions=row_decisions,
            idempotency_key=idempotency_key,
        )
        
        messages.success(request, "Importação confirmada com sucesso!")
        return redirect("finance:import-report", profile_id=profile.pk, batch_id=batch.pk)
        
    except ImportCommitError as e:
        messages.error(request, str(e))
    except ValidationError as e:
        messages.error(request, "; ".join(e.messages))
    except Exception as e:
        messages.error(request, f"Erro inesperado: {str(e)}")
    
    return redirect("finance:import-preview", profile_id=profile.pk, batch_id=batch.pk)


# =============================================================================
# Relatório de Importação
# =============================================================================

@login_required
@require_http_methods(["GET"])
def import_report(request, profile_id, batch_id):
    """Relatório detalhado pós-importação."""
    profile = require_module(request.user, profile_id, "accounts", "view")
    require_module(request.user, profile_id, "movements", "view")
    
    batch = get_object_or_404(
        ImportBatch.objects.select_related("profile", "account", "created_by"),
        pk=batch_id, profile=profile
    )
    
    report = generate_import_report(batch)
    
    return render(request, "finance/import_report.html", {
        "workspace": profile.workspace,
        "profile": profile,
        "batch": batch,
        "report": report,
        "cancel_url": _import_return_url(profile),
    })


# =============================================================================
# API para Edição Inline de Linhas (HTMX)
# =============================================================================

@login_required
@require_http_methods(["GET", "POST"])
def import_row_edit(request, profile_id, batch_id, row_id):
    """Edição inline de uma linha de importação (modal HTMX)."""
    profile = require_module(request.user, profile_id, "movements", "edit")
    
    batch = get_object_or_404(ImportBatch, pk=batch_id, profile=profile)
    row = get_object_or_404(ImportRow, pk=row_id, batch=batch)
    
    accounts = BankAccount.objects.filter(profile=profile, is_archived=False)
    
    if request.method == "POST":
        # Atualizar campos editáveis
        row.description = request.POST.get("description", row.description)[:255]
        row.memo = request.POST.get("memo", row.memo)[:2000]
        
        # Valor ajustado
        try:
            adjusted_amount = Decimal(request.POST.get("amount", "0"))
            if adjusted_amount > 0:
                row.amount = adjusted_amount if not row.is_credit else -adjusted_amount
        except (ValueError, ArithmeticError, TypeError):
            pass
        
        # Tipo ajustado
        adjusted_kind = request.POST.get("kind")
        if adjusted_kind:
            row.suggested_kind = adjusted_kind
        
        row.save(update_fields=["description", "memo", "amount", "suggested_kind"])
        
        return render(request, "finance/import_row_row.html", {
            "row": row,
            "batch": batch,
            "accounts": accounts,
        })
    
    return render(request, "finance/import_row_edit.html", {
        "row": row,
        "batch": batch,
        "accounts": accounts,
        "kinds": [
            ("recurring", "Pagamento previsível"),
            ("unexpected", "Despesa imprevisível"),
            ("application", "Aplicação"),
            ("withdrawal", "Resgate"),
            ("transfer", "Transferência"),
            ("income", "Recebimento"),
        ],
    })


@login_required
@require_http_methods(["GET"])
def import_row_detail(request, profile_id, batch_id, row_id):
    """Detalhe de uma linha (para modal de visualização)."""
    profile = require_module(request.user, profile_id, "movements", "view")
    
    batch = get_object_or_404(ImportBatch, pk=batch_id, profile=profile)
    row = get_object_or_404(ImportRow.objects.select_related("linked_batch"), pk=row_id, batch=batch)
    
    suggestion = None
    if row.status in [ImportRow.Status.SUGGESTED, ImportRow.Status.DUPLICATE]:
        suggestions = generate_reconciliation_suggestions(batch)
        for s in suggestions:
            if s.import_row.pk == row.pk:
                suggestion = s
                break
    
    return render(request, "finance/import_row_detail.html", {
        "row": row,
        "batch": batch,
        "suggestion": suggestion,
        "profile": profile,
    })