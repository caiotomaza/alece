# SPDX-License-Identifier: GPL-3.0-only
"""Views para gerenciamento de regras de categorização De-Para."""
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST

from apps.core.permissions import require_workspace_admin, user_can_module
from apps.finance.models import (
    CategorizationRule, FinancialProfile,
)
from apps.finance.services.categorization import (
    create_categorization_rule, update_categorization_rule, delete_categorization_rule,
    get_categorization_rules,
    RegexSecurityError,
)


# =============================================================================
# Helpers
# =============================================================================

def _categorization_return_url(workspace_id, profile_id=None):
    url = reverse("finance:categorization-list", args=[workspace_id])
    if profile_id:
        url += f"?profile={profile_id}"
    return url


# =============================================================================
# Listagem de Regras
# =============================================================================

@login_required
@require_http_methods(["GET"])
def categorization_list(request, workspace_id):
    """Lista regras de categorização do workspace."""
    workspace = require_workspace_admin(request.user, workspace_id)
    
    profile_id = request.GET.get("profile")
    profile = None
    if profile_id:
        profile = get_object_or_404(FinancialProfile, pk=profile_id, workspace=workspace)
    
    # Obter regras (perfil + núcleo)
    rules = get_categorization_rules(workspace_id, profile_id=profile.pk if profile else None)
    
    # Perfis para filtro
    profiles = FinancialProfile.objects.filter(workspace=workspace, is_archived=False)
    
    return render(request, "finance/categorization_list.html", {
        "workspace": workspace,
        "profile": profile,
        "rules": rules,
        "profiles": profiles,
        "selected_profile": profile.pk if profile else None,
        "can_manage": user_can_module(request.user, workspace_id, "accounts", "edit"),
    })


# =============================================================================
# Criação de Regra
# =============================================================================

@login_required
@require_http_methods(["GET", "POST"])
def categorization_create(request, workspace_id):
    """Cria nova regra de categorização."""
    workspace = require_workspace_admin(request.user, workspace_id)
    
    profile_id = request.GET.get("profile") or request.POST.get("profile")
    profile = None
    if profile_id:
        profile = get_object_or_404(FinancialProfile, pk=profile_id, workspace=workspace)
    
    profiles = FinancialProfile.objects.filter(workspace=workspace, is_archived=False)
    
    if request.method == "POST":
        try:
            rule = create_categorization_rule(
                actor=request.user,
                workspace_id=workspace.pk,
                profile_id=profile.pk if profile else None,
                name=request.POST.get("name", "").strip(),
                match_type=request.POST.get("match_type", "exact"),
                pattern=request.POST.get("pattern", "").strip(),
                match_field=request.POST.get("match_field", "both"),
                suggested_kind=request.POST.get("suggested_kind", ""),
                suggested_link=_parse_json_field(request.POST.get("suggested_link", "{}")),
                priority=int(request.POST.get("priority", 100)),
                case_sensitive=bool(request.POST.get("case_sensitive")),
                match_field_enum=request.POST.get("match_field", "both"),
                description=request.POST.get("description", "").strip(),
            )
            messages.success(request, f"Regra '{rule.name}' criada com sucesso.")
            return redirect(_categorization_return_url(workspace_id, profile.pk if profile else None))
        except ValidationError as e:
            messages.error(request, "; ".join(e.messages))
        except RegexSecurityError as e:
            messages.error(request, f"Erro de segurança na regex: {e}")
        except Exception as e:
            messages.error(request, f"Erro inesperado: {e}")
    
    return render(request, "finance/categorization_form.html", {
        "workspace": workspace,
        "profile": profile,
        "profiles": profiles,
        "selected_profile": profile.pk if profile else None,
        "match_types": CategorizationRule.MatchType.choices,
        "match_fields": CategorizationRule.MatchField.choices,
        "kinds": CategorizationRule.Kind.choices,
        "cancel_url": _categorization_return_url(workspace_id, profile.pk if profile else None),
    })


# =============================================================================
# Edição de Regra
# =============================================================================

@login_required
@require_http_methods(["GET", "POST"])
def categorization_edit(request, workspace_id, rule_id):
    """Edita regra de categorização existente."""
    workspace = require_workspace_admin(request.user, workspace_id)
    rule = get_object_or_404(CategorizationRule, pk=rule_id, workspace=workspace)
    
    profile = rule.profile
    profiles = FinancialProfile.objects.filter(workspace=workspace, is_archived=False)
    
    if request.method == "POST":
        try:
            rule = update_categorization_rule(
                actor=request.user,
                rule_id=rule.pk,
                workspace_id=workspace.pk,
                name=request.POST.get("name", "").strip(),
                match_type=request.POST.get("match_type", rule.match_type),
                pattern=request.POST.get("pattern", "").strip(),
                match_field=request.POST.get("match_field", rule.match_field),
                suggested_kind=request.POST.get("suggested_kind", rule.suggested_kind),
                suggested_link=_parse_json_field(request.POST.get("suggested_link", "{}")),
                priority=int(request.POST.get("priority", rule.priority)),
                case_sensitive=bool(request.POST.get("case_sensitive", rule.case_sensitive)),
                description=request.POST.get("description", "").strip(),
                is_active=bool(request.POST.get("is_active")),
            )
            messages.success(request, f"Regra '{rule.name}' atualizada com sucesso.")
            return redirect(_categorization_return_url(workspace_id, profile.pk if profile else None))
        except ValidationError as e:
            messages.error(request, "; ".join(e.messages))
        except RegexSecurityError as e:
            messages.error(request, f"Erro de segurança na regex: {e}")
        except Exception as e:
            messages.error(request, f"Erro inesperado: {e}")
    
    return render(request, "finance/categorization_form.html", {
        "workspace": workspace,
        "profile": profile,
        "profiles": profiles,
        "rule": rule,
        "selected_profile": profile.pk if profile else None,
        "match_types": CategorizationRule.MatchType.choices,
        "match_fields": CategorizationRule.MatchField.choices,
        "kinds": CategorizationRule.Kind.choices,
        "cancel_url": _categorization_return_url(workspace_id, profile.pk if profile else None),
        "is_edit": True,
    })


# =============================================================================
# Exclusão de Regra
# =============================================================================

@login_required
@require_POST
def categorization_delete(request, workspace_id, rule_id):
    """Exclui regra de categorização."""
    workspace = require_workspace_admin(request.user, workspace_id)
    rule = get_object_or_404(CategorizationRule, pk=rule_id, workspace=workspace)
    profile = rule.profile
    
    try:
        delete_categorization_rule(
            actor=request.user,
            rule_id=rule.pk,
            workspace_id=workspace.pk,
        )
        messages.success(request, f"Regra '{rule.name}' excluída com sucesso.")
    except Exception as e:
        messages.error(request, f"Erro ao excluir: {e}")
    
    return redirect(_categorization_return_url(workspace_id, profile.pk if profile else None))


# =============================================================================
# Teste de Regra (AJAX)
# =============================================================================

@login_required
@require_http_methods(["POST"])
def categorization_test(request, workspace_id):
    """Testa uma regra contra uma descrição/memo (AJAX)."""
    require_workspace_admin(request.user, workspace_id)
    
    pattern = request.POST.get("pattern", "")
    match_type = request.POST.get("match_type", "exact")
    match_field = request.POST.get("match_field", "both")
    case_sensitive = bool(request.POST.get("case_sensitive"))
    test_description = request.POST.get("description", "")
    test_memo = request.POST.get("memo", "")
    
    try:
        from apps.finance.models import CategorizationRule
        
        if match_type == CategorizationRule.MatchType.REGEX:
            from apps.finance.services.categorization import compile_safe_regex
            compile_safe_regex(pattern, case_sensitive)
        
        # Simular correspondência
        from apps.finance.services.importers import ParsedTransaction
        test_txn = ParsedTransaction(
            description=test_description,
            memo=test_memo,
        )
        
        # Criar regra temporária para teste
        temp_rule = CategorizationRule(
            match_type=match_type,
            pattern=pattern,
            match_field=match_field,
            case_sensitive=case_sensitive,
            suggested_kind="unexpected",
        )
        
        from apps.finance.services.categorization import apply_categorization_rules
        kind, link, confidence, justification = apply_categorization_rules(test_txn, [temp_rule])
        
        return render(request, "finance/categorization_test_result.html", {
            "matched": kind != "unexpected" or confidence > Decimal("0.30"),
            "kind": kind,
            "confidence": confidence,
            "justification": justification,
            "test_description": test_description,
            "test_memo": test_memo,
        })
    except RegexSecurityError as e:
        return render(request, "finance/categorization_test_result.html", {
            "error": f"Regex insegura: {e}",
        })
    except Exception as e:
        return render(request, "finance/categorization_test_result.html", {
            "error": f"Erro: {e}",
        })


# =============================================================================
# Helper
# =============================================================================

def _parse_json_field(value: str) -> dict:
    """Parse seguro de campo JSON."""
    import json
    try:
        return json.loads(value) if value else {}
    except json.JSONDecodeError:
        return {}