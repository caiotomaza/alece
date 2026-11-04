# SPDX-License-Identifier: GPL-3.0-only
"""Settings dashboard separated by workspace administrator role; no front-end-only authorization."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError, ImproperlyConfigured
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods, require_POST

from apps.core.ai_service import build_financial_payload, send_to_ai_provider
from apps.core.ai_catalog import PROVIDERS, SECTIONS
from apps.core.ai_credentials import write_token, read_token, delete_token, has_token
from apps.core.auth_services import issue_recovery_codes, acknowledge_recovery_codes
import secrets
from apps.core.models import AIAnalysis, AIProviderConfig, SystemLog, UserProfile, RecoveryCode
from apps.core.permissions import get_accessible_profiles, require_workspace_access, require_workspace_admin, user_is_workspace_admin
from apps.core.settings_forms import AIProviderConfigForm, PersonalInformationForm
from apps.finance.models import FinancialProfile, ReportExport, WorkspaceMembership


def _personal_context(request):
    from apps.finance.public_routes import active_workspace_id
    workspace_id = active_workspace_id(request)
    if workspace_id is None:
        return {"active_nav": "settings"}
    workspace = require_workspace_access(request.user, workspace_id)
    return {"workspace": workspace, "active_nav": "settings",
            "nav_profiles": list(get_accessible_profiles(request.user).filter(
                workspace=workspace, is_archived=False).order_by("pk"))}


def _audit(user, workspace, action, description, details=None):
    SystemLog.objects.create(
        module=SystemLog.Module.SETTINGS, action=action, result=SystemLog.Result.SUCCESS,
        severity=SystemLog.Severity.INFO, user=user, workspace=workspace,
        description=description, details=details or {},
    )


def _apply_selected_profile(request, workspace):
    """Only an authorized profile may change the navigation preference."""
    from apps.finance.profile_selection import remember_profile
    if "profiles" not in request.GET:
        return
    selected = request.GET.getlist("profiles")
    if selected == ["all"]:
        remember_profile(request, workspace.pk, None)
    elif len(selected) == 1 and selected[0].isdecimal():
        chosen = int(selected[0])
        if not get_accessible_profiles(request.user).filter(
            pk=chosen, workspace=workspace, is_archived=False,
        ).exists():
            raise PermissionDenied("Perfil não autorizado.")
        remember_profile(request, workspace.pk, chosen)
    else:
        raise PermissionDenied("Seleção inválida de perfil.")


def _base_settings_context(request, workspace):
    return {
        "workspace": workspace,
        "active_nav": "settings",
        "is_workspace_admin": user_is_workspace_admin(request.user, workspace.pk),
        "nav_profiles": list(get_accessible_profiles(request.user).filter(
            workspace=workspace, is_archived=False).order_by("pk")),
    }


@never_cache
@login_required
@require_http_methods(["GET"])
def settings_dashboard(request, workspace_id):
    """Shortcuts only: no administrative record table on the settings landing."""
    workspace = require_workspace_access(request.user, workspace_id)
    _apply_selected_profile(request, workspace)
    context = _base_settings_context(request, workspace)
    context["title"] = "Configurações"
    return render(request, "core/settings_dashboard.html", context)


@never_cache
@login_required
@require_http_methods(["GET"])
def settings_admin_panel(request, panel):
    """Dedicated management windows with server-side workspace authorization."""
    from apps.finance.public_routes import active_workspace_id
    workspace_id = active_workspace_id(request)
    if workspace_id is None:
        return redirect("home")
    workspace = require_workspace_admin(request.user, workspace_id)
    _apply_selected_profile(request, workspace)
    names = {"usuarios": "Gerenciar usuários", "perfis": "Gerenciar perfis financeiros", "apis": "Gerenciar APIs de IA"}
    if panel not in names:
        raise PermissionDenied("Área de administração inexistente.")
    context = _base_settings_context(request, workspace)
    context.update({"panel": panel, "title": names[panel]})
    if panel == "usuarios":
        context["memberships"] = WorkspaceMembership.objects.filter(workspace=workspace).select_related("user").order_by("user__username")
    elif panel == "perfis":
        context["profiles"] = FinancialProfile.objects.filter(workspace=workspace, deleted_at__isnull=True).order_by("is_archived", "name")
    else:
        context["providers"] = AIProviderConfig.objects.filter(workspace=workspace).order_by("-enabled", "name")
        context["active_profiles"] = FinancialProfile.objects.filter(workspace=workspace, is_archived=False, deleted_at__isnull=True)
    return render(request, "core/settings_admin_panel.html", context)


@never_cache
@sensitive_post_parameters("current_password")
@login_required
@require_http_methods(["GET", "POST"])
def my_information(request):
    User = get_user_model()
    account = User.objects.get(pk=request.user.pk)
    form = PersonalInformationForm(request.POST if request.method == "POST" else None, instance=account)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            # Recheck password using locked row to prevent concurrent updates.
            locked = User.objects.select_for_update().get(pk=request.user.pk)
            if not locked.check_password(form.cleaned_data["current_password"]):
                form.add_error("current_password", "A senha mudou; tente novamente.")
            else:
                for field in ("username", "first_name", "last_name", "email"):
                    setattr(locked, field, form.cleaned_data[field])
                locked.full_clean(exclude=["password"])
                locked.save(update_fields=["username", "first_name", "last_name", "email"])
                _audit(locked, None, SystemLog.Action.UPDATE,
                       "Dados da própria conta alterados", {"fields": ["username", "first_name", "last_name", "email"]})
                messages.success(request, "Informações atualizadas.")
                return redirect("configuracoes")
    return render(request, "core/settings_form.html", {
        **_personal_context(request),
        "form": form, "title": "Editar suas informações", "submit_label": "Salvar informações",
    })


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def recovery_status(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    count = RecoveryCode.objects.filter(user=request.user, used_at__isnull=True).count()
    if request.method == "POST":
        nonce = request.session.get("alece_recovery_nonce", "")
        if not nonce or not secrets.compare_digest(nonce, request.POST.get("nonce", "")):
            messages.error(request, "A confirmação expirou. Gere novos códigos e salve-os.")
        elif request.POST.get("copied") != "1" or request.POST.get("downloaded") != "1":
            messages.error(request, "Copie e baixe os seis códigos antes de continuar.")
        elif count != 6 or not acknowledge_recovery_codes(request.user.pk):
            messages.error(request, "Os códigos não estão disponíveis. Gere um novo conjunto.")
        else:
            request.session.pop("alece_recovery_nonce", None)
            messages.success(request, "Códigos guardados e recuperação da conta ativada.")
            return redirect("configuracoes")
    # Este endpoint não é mais uma tela de consulta. Valores antigos existem
    # apenas como hashes; nunca montar um modal sem códigos legíveis.
    if request.method == "GET" and count == 0 and profile.recovery_acknowledged_at is None:
        codes = issue_recovery_codes(request.user.pk, onboarding=True)
        if codes:
            request.session["alece_recovery_nonce"] = secrets.token_urlsafe(32)
            return render(request, "core/recovery_status.html", {
                **_personal_context(request), "codes": codes, "recovery_count": 6,
                "nonce": request.session["alece_recovery_nonce"],
            })
    if profile.recovery_acknowledged_at is None:
        # Interrompeu a emissão antes da confirmação: um novo conjunto exige
        # reautenticação em vez de abrir um modal inútil ou expor hashes.
        request.session.pop("alece_recovery_nonce", None)
        return redirect("recovery_generate")
    if count == 0:
        # Se todos os códigos foram utilizados, a configuração volta a ser
        # obrigatória. Evite loop de redirecionamento com o middleware.
        return redirect("recovery_generate")
    return redirect("configuracoes")



def _set_active_ai_provider_locked(workspace, selected_id):
    """Chamar dentro de transaction.atomic() com Workspace bloqueado via select_for_update.

    O índice único parcial no PostgreSQL impede corridas e configurações ambíguas.
    """
    AIProviderConfig.objects.filter(workspace=workspace, enabled=True).exclude(pk=selected_id).update(enabled=False)
    if selected_id is not None:
        AIProviderConfig.objects.filter(workspace=workspace, pk=selected_id).update(enabled=True)


def _ai_provider_is_ready(provider):
    """Nenhuma ativação sem credencial; host personalizado mantém allowlist na execução."""
    return bool(has_token(provider.pk) or provider.api_key_env)



@sensitive_post_parameters("api_token")
@login_required
@require_http_methods(["GET", "POST"])
def provider_form(request, provider_id=None):
    from apps.finance.public_routes import active_workspace_id
    from apps.finance.models import Workspace
    workspace_id = active_workspace_id(request)
    if workspace_id is None:
        raise PermissionDenied("Selecione um núcleo autorizado.")
    workspace = require_workspace_admin(request.user, workspace_id)
    provider = get_object_or_404(AIProviderConfig, workspace=workspace, pk=provider_id) if provider_id else None
    form = AIProviderConfigForm(
        request.POST if request.method == "POST" else None, instance=provider,
        has_active_provider=AIProviderConfig.objects.filter(workspace=workspace, enabled=True).exists(),
    )
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        # Proteção contra sobrescrita de nomes e mudança simultânea de integração.
        dupe = AIProviderConfig.objects.filter(workspace=workspace, name=data["provider_name"])
        if provider is not None:
            dupe = dupe.exclude(pk=provider.pk)
        if dupe.exists():
            form.add_error("provider_name" if data["provider_type"] == "custom" else "provider_type",
                           "Essa integração já existe neste núcleo.")
        else:
            token_before = None
            token_changed_id = None
            try:
                with transaction.atomic():
                    Workspace.objects.select_for_update().get(pk=workspace.pk)
                    entry = (AIProviderConfig.objects.select_for_update().get(pk=provider.pk, workspace=workspace)
                             if provider is not None else AIProviderConfig(workspace=workspace))
                    entry.name = data["provider_name"]
                    entry.endpoint = data["endpoint"]
                    entry.model_name = data["model_name"]
                    entry.api_key_env = "" if data["api_token"] else entry.api_key_env
                    entry.sections = list(SECTIONS)
                    # Não ativar ao salvar antes de escrever a chave.
                    entry.enabled = False
                    entry.save()
                    if data["api_token"]:
                        # O arquivo de chave não participa da transação SQL; manter
                        # a versão anterior em memória para rollback de falha no DB.
                        token_before = read_token(entry.pk)
                        write_token(entry.pk, data["api_token"])
                        token_changed_id = entry.pk
                    if data["enabled"]:
                        if not _ai_provider_is_ready(entry):
                            raise ValidationError("Cadastre a chave antes de ativar a integração.")
                        _set_active_ai_provider_locked(workspace, entry.pk)
                    _audit(request.user, workspace,
                           SystemLog.Action.UPDATE if provider else SystemLog.Action.CREATE,
                           "Integração de IA salva", {"provider_id": entry.pk, "active": bool(data["enabled"])})
            except (OSError, ValueError, ValidationError, IntegrityError, ImproperlyConfigured):
                if token_changed_id is not None:
                    try:
                        if token_before:
                            write_token(token_changed_id, token_before)
                        else:
                            delete_token(token_changed_id)
                    except (OSError, ImproperlyConfigured):
                        form.add_error(None, "Falha ao reverter a chave. Desative a integração e revise o volume privado antes de reutilizá-la.")
                form.add_error(None, "Não foi possível salvar a integração. Verifique a chave, os campos e as permissões do serviço.")
            else:
                messages.success(request, "Integração salva. Nenhum dado financeiro foi enviado.")
                return redirect("configuracoes-apis")
    return render(request, "core/settings_form.html", {
        **_personal_context(request), "form": form, "is_ai_form": True,
        "ai_preset_map": PROVIDERS,
        "title": "Editar integração de IA" if provider else "Nova integração de IA",
        "submit_label": "Salvar integração",
    })


@login_required
@require_POST
def provider_select(request, provider_id):
    """Alternância exclusiva, auditada e protegida contra requisições concorrentes."""
    from apps.finance.public_routes import active_workspace_id
    from apps.finance.models import Workspace
    workspace_id = active_workspace_id(request)
    if workspace_id is None:
        raise PermissionDenied("Selecione um núcleo autorizado.")
    workspace = require_workspace_admin(request.user, workspace_id)
    wanted = request.POST.get("enabled")
    if wanted not in ("0", "1"):
        raise PermissionDenied("Estado de integração inválido.")
    with transaction.atomic():
        Workspace.objects.select_for_update().get(pk=workspace.pk)
        entry = get_object_or_404(AIProviderConfig.objects.select_for_update(), workspace=workspace, pk=provider_id)
        if wanted == "1":
            if not _ai_provider_is_ready(entry):
                messages.error(request, "Cadastre uma chave para ativar esta integração.")
                return redirect("configuracoes-apis")
            _set_active_ai_provider_locked(workspace, entry.pk)
        else:
            AIProviderConfig.objects.filter(pk=entry.pk, workspace=workspace).update(enabled=False)
        _audit(request.user, workspace, SystemLog.Action.UPDATE, "Seleção de integração de IA alterada",
               {"provider_id": entry.pk, "active": wanted == "1"})
    messages.success(request, "Integração selecionada." if wanted == "1" else "Integração desativada.")
    return redirect("configuracoes-apis")


@login_required
@require_POST
def provider_delete(request, provider_id):
    from apps.finance.public_routes import active_workspace_id
    workspace_id = active_workspace_id(request)
    if workspace_id is None:
        raise PermissionDenied("Selecione um núcleo autorizado.")
    workspace = require_workspace_admin(request.user, workspace_id)
    from apps.finance.models import Workspace
    with transaction.atomic():
        Workspace.objects.select_for_update().get(pk=workspace.pk)
        entry = get_object_or_404(AIProviderConfig.objects.select_for_update(), workspace=workspace, pk=provider_id)
        # A revogação da chave é deliberadamente fail-closed. Se a gravação SQL
        # subsequente falhar, a chave anterior terá de ser informada novamente.
        # Não salvamos credenciais revogadas em logs ou backups exportáveis.
        try:
            delete_token(entry.pk)
        except (OSError, ImproperlyConfigured):
            messages.error(request, "Não foi possível revogar a chave privada. Verifique as permissões do volume.")
            return redirect("configuracoes-apis")
        if AIAnalysis.objects.filter(provider=entry).exists():
            entry.enabled = False
            entry.api_key_env = ""
            entry.save(update_fields=["enabled", "api_key_env", "updated_at"])
            messages.info(request, "Integração desativada e chave local revogada; histórico de análises preservado.")
        else:
            entry.delete()
            messages.success(request, "Integração excluída e chave local revogada.")
        _audit(request.user, workspace, SystemLog.Action.UPDATE,
               "Integração de IA excluída ou desativada", {"provider_id": provider_id})
    return redirect("configuracoes-apis")


@never_cache
@login_required
@require_POST
def analyze_imports(request, provider_id):
    from apps.finance.public_routes import active_workspace_id
    workspace_id = active_workspace_id(request)
    if workspace_id is None:
        raise PermissionDenied("Selecione um núcleo autorizado.")
    workspace = require_workspace_admin(request.user, workspace_id)
    provider = get_object_or_404(AIProviderConfig, workspace=workspace, pk=provider_id, enabled=True)
    section = request.POST.get("section")
    profile_id = request.POST.get("profile")
    if section not in provider.sections or section not in dict(AIProviderConfig.Section.choices):
        raise PermissionDenied("Área não autorizada para esta integração.")
    if not request.POST.get("consent") == "yes":
        messages.error(request, "Confirme o envio dos dados para a API externa.")
        return redirect("configuracoes-apis")
    profile = get_object_or_404(FinancialProfile, workspace=workspace, pk=profile_id, is_archived=False)
    payload, data_hash = build_financial_payload(profile, section)
    if not payload["records"]:
        messages.error(request, "Nenhum registro importado e confirmado disponível para esta análise.")
        return redirect("configuracoes-apis")
    try:
        summary = send_to_ai_provider(provider, payload)
    except ValidationError as error:
        SystemLog.objects.create(
            module=SystemLog.Module.SETTINGS, action=SystemLog.Action.ERROR,
            result=SystemLog.Result.FAILURE, severity=SystemLog.Severity.WARNING,
            workspace=workspace, user=request.user,
            description="Falha em análise de IA solicitada", details={"provider_id": provider.pk, "section": section},
        )
        messages.error(request, error.messages[0])
        return redirect("configuracoes-apis")
    AIAnalysis.objects.create(
        workspace=workspace, profile=profile, provider=provider, section=section,
        summary=summary, data_hash=data_hash, record_count=len(payload["records"]),
        created_by=request.user,
    )
    _audit(request.user, workspace, SystemLog.Action.CREATE,
           "Análise de IA solicitada por administrador", {"provider_id": provider.pk, "section": section, "rows": len(payload["records"])})
    messages.success(request, "Análise recebida e publicada na área selecionada.")
    return redirect({"expenses": "despesas", "investments": "investimentos", "movements": "movimentacoes"}[section])
