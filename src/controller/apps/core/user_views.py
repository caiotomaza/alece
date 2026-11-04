# SPDX-License-Identifier: GPL-3.0-only
"""Views for first-run setup and workspace user management."""
from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DatabaseError, transaction
from django.http import HttpResponseForbidden
from django.contrib.auth import get_user_model
import secrets
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.views.decorators.debug import sensitive_post_parameters

from apps.core.session_security import revoke_db_sessions_for_user

from apps.core.bootstrap import create_initial_admin, is_system_initialized, setup_is_host_bound
from apps.core.forms import (
    BootstrapSetupForm, UserManagementForm, UserEditForm, UserPasswordResetForm,
)
from apps.core.models import UserProfile
from apps.core.permissions import require_workspace_admin, require_workspace_access
from apps.finance.models import FinancialProfile, ProfileGrant, Workspace, WorkspaceMembership
from apps.finance.services.system_log import log_financial_operation


@sensitive_post_parameters("password1", "password2")
@require_http_methods(["GET", "POST"])
def setup_view(request):
    """First-run setup is available only while the host binding is loopback."""
    if not setup_is_host_bound():
        return HttpResponseForbidden("Primeira configuração disponível somente no host ou túnel.")
    if is_system_initialized():
        return redirect("login")

    form = BootstrapSetupForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            first_admin = create_initial_admin(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password1"],
                email=form.cleaned_data.get("email", ""),
            )
        except ValidationError:
            return redirect("login")
        except DatabaseError:
            messages.error(request, "Não foi possível concluir a configuração inicial.")
        else:
            login(request, first_admin, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, "Configure seus seis códigos de recuperação para concluir o primeiro acesso.")
            return redirect("configuracoes-codigos")

    return render(request, "core/setup.html", {
        "form": form,
        "title": "Configuração Inicial",
    })


@sensitive_post_parameters("password", "password1", "password2")
@login_required
@require_http_methods(["GET", "POST"])
def user_management(request, workspace_id):
    """Gestão de usuários no workspace (apenas para Administradores)."""
    require_workspace_access(request.user, workspace_id)
    require_workspace_admin(request.user, workspace_id)

    workspace = Workspace.objects.get(pk=workspace_id)
    memberships = WorkspaceMembership.objects.filter(
        workspace=workspace
    ).select_related("user", "user__profile")

    if request.method == "POST":
        # Criação de novo usuário
        form = UserManagementForm(request.POST, requesting_user=request.user, target_workspace=workspace)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save()
                    WorkspaceMembership.objects.create(
                        workspace=workspace,
                        user=user,
                        role=form.cleaned_data["role"],
                    )
                    # Criar UserProfile
                    UserProfile.objects.get_or_create(user=user)

                    # Log do evento de criação de usuário
                    log_financial_operation(
                        action="create",
                        result="success",
                        description=f"Usuário criado: '{user.username}' com papel {form.cleaned_data['role']}",
                        workspace=workspace,
                        profile=None,
                        user=request.user,
                        request=request,
                        object_type="User",
                        object_id=str(user.pk),
                        object_repr=user.username,
                        details={"role": form.cleaned_data["role"]},
                        ledger_batch_id="",
                        result_status="success",
                        severity="info",
                    )

                    messages.success(request, f"Usuário '{user.username}' criado com sucesso.")
                    return redirect("configuracoes-usuarios")
            except ValidationError as e:
                form.add_error(None, e)
        else:
            # Formulário inválido - será renderizado com erros
            pass
    else:
        form = UserManagementForm(requesting_user=request.user, target_workspace=workspace)

    return render(request, "core/user_management.html", {
        "workspace": workspace,
        "memberships": memberships,
        "form": form,
        "active_nav": "settings",
        "title": "Gestão de Usuários",
    })


@login_required
@require_http_methods(["GET", "POST"])
def user_edit(request, workspace_id, user_id):
    """Edição de usuário existente."""
    require_workspace_access(request.user, workspace_id)
    require_workspace_admin(request.user, workspace_id)

    workspace = Workspace.objects.get(pk=workspace_id)
    membership = get_object_or_404(WorkspaceMembership, workspace=workspace, user_id=user_id)
    target_user = membership.user
    if target_user.is_superuser and not request.user.is_superuser:
        raise PermissionDenied("Alterações em superusuários globais exigem administração do sistema.")

    # Impedir edição do próprio usuário para mudança de papel/ativação
    if target_user == request.user:
        messages.error(request, "Você não pode alterar seu próprio papel ou status de ativação.")
        return redirect("configuracoes-usuarios")

    # Impedir desativação do último admin ativo
    active_admins = WorkspaceMembership.objects.filter(
        workspace=workspace, role="admin", user__is_active=True
    ).count()

    if request.method == "POST":
        form = UserEditForm(request.POST, instance=target_user, requesting_user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Verificar se está tentando desativar o último admin
                    new_role = form.cleaned_data["role"]
                    new_active = form.cleaned_data["is_active"]

                    other_workspaces = WorkspaceMembership.objects.filter(user=target_user).exclude(workspace=workspace).exists()
                    if other_workspaces and (new_active != target_user.is_active or
                                             form.cleaned_data["username"] != target_user.username or
                                             form.cleaned_data["email"] != target_user.email):
                        form.add_error(None, "Nome e estado global não podem ser alterados por um administrador de apenas um dos núcleos desta conta.")
                    elif membership.role == "admin" and new_role != "admin" and active_admins <= 1:
                        form.add_error("role", "Não é possível remover o último Administrador ativo.")
                    elif membership.role == "admin" and membership.user.is_active and not new_active and active_admins <= 1:
                        form.add_error("is_active", "Não é possível desativar o último Administrador ativo.")
                    else:
                        old_role = membership.role
                        old_active = target_user.is_active
                        old_email = target_user.email

                        form.save()
                        membership.role = new_role
                        membership.save(update_fields=["role"])

                        # Log do evento de edição de usuário
                        changes = {}
                        if old_role != new_role:
                            changes["role"] = {"old": old_role, "new": new_role}
                        if old_active != new_active:
                            changes["is_active"] = {"old": str(old_active), "new": str(new_active)}
                        if old_email != target_user.email:
                            changes["email"] = "alterado"

                        if changes:
                            log_financial_operation(
                                action="update",
                                result="success",
                                description=f"Usuário atualizado: '{target_user.username}'",
                                workspace=workspace,
                                profile=None,
                                user=request.user,
                                request=request,
                                object_type="User",
                                object_id=str(target_user.pk),
                                object_repr=target_user.username,
                                details={"changes": changes},
                                ledger_batch_id="",
                                result_status="success",
                                severity="info",
                            )

                        messages.success(request, f"Usuário '{target_user.username}' atualizado.")
                        return redirect("configuracoes-usuarios")
            except ValidationError as e:
                form.add_error(None, e)
        # Se form inválido ou erro de validação (last admin), renderiza com erros
    else:
        form = UserEditForm(instance=target_user, requesting_user=request.user)
        form.initial["role"] = membership.role
        form.initial["is_active"] = target_user.is_active

    grants = {g.profile_id: g for g in ProfileGrant.objects.filter(membership=membership)}
    fields = ("overview_level", "accounts_level", "expenses_level", "investments_level", "movements_level")
    grant_data = []
    for profile in FinancialProfile.objects.filter(workspace=workspace, is_archived=False):
        grant = grants.get(profile.pk)
        levels = [getattr(grant, key) for key in fields] if grant else []
        grant_data.append({
            "profile": profile,
            "grant": grant,
            "all_view": bool(levels) and all(value != ProfileGrant.Level.NONE for value in levels),
            "all_edit": bool(levels) and all(value == ProfileGrant.Level.EDIT for value in levels),
        })
    return render(request, "core/user_edit.html", {
        "grant_data": grant_data,
        "workspace": workspace,
        "target_user": target_user,
        "membership": membership,
        "form": form,
        "active_nav": "settings",
        "title": f"Editar usuário: {target_user.username}",
    })


def _authorize_global_account_action(actor, target, workspace_id):
    """Um admin local não pode afetar credenciais/sessões em outros núcleos."""
    if target.is_superuser and not actor.is_superuser:
        raise PermissionDenied("Contas globais exigem administração do sistema.")
    if not actor.is_superuser and WorkspaceMembership.objects.filter(
        user=target,
    ).exclude(workspace_id=workspace_id).exists():
        raise PermissionDenied("A conta participa de outro espaço; esta ação global não é permitida.")


@sensitive_post_parameters("new_password1", "new_password2")
@login_required
@require_http_methods(["GET", "POST"])
def user_password_reset(request, workspace_id, user_id):
    """Redefinição de senha por administrador."""
    require_workspace_access(request.user, workspace_id)
    require_workspace_admin(request.user, workspace_id)

    workspace = Workspace.objects.get(pk=workspace_id)
    membership = get_object_or_404(WorkspaceMembership, workspace=workspace, user_id=user_id)
    target_user = membership.user
    _authorize_global_account_action(request.user, target_user, workspace_id)

    if target_user == request.user:
        messages.error(request, "Use 'Alterar senha' para mudar sua própria senha.")
        return redirect("configuracoes-usuarios")

    if request.method == "POST":
        form = UserPasswordResetForm(target_user, request.POST, requesting_user=request.user, target_user=target_user)
        if form.is_valid():
            with transaction.atomic():
                form.save()
                revoked_count = revoke_db_sessions_for_user(target_user.pk)
            # A sessão do administrador não foi modificada: não atualizar o hash dela.

            # Log do evento de redefinição de senha
            log_financial_operation(
                action="update",
                result="success",
                description=f"Senha redefinida por administrador: '{target_user.username}'",
                workspace=workspace,
                profile=None,
                user=request.user,
                request=request,
                object_type="User",
                object_id=str(target_user.pk),
                object_repr=target_user.username,
                details={"reset_by_admin": True, "revoked_sessions": revoked_count},
                ledger_batch_id="",
                result_status="success",
                severity="warning",
            )

            messages.success(request, f"Senha de '{target_user.username}' redefinida com sucesso.")
            return redirect("configuracoes-usuarios")
    else:
        form = UserPasswordResetForm(target_user, requesting_user=request.user, target_user=target_user)

    return render(request, "core/user_password_reset.html", {
        "workspace": workspace,
        "target_user": target_user,
        "form": form,
        "active_nav": "settings",
        "title": f"Redefinir senha: {target_user.username}",
    })


@login_required
@require_http_methods(["POST"])
def user_revoke_sessions(request, workspace_id, user_id):
    """Revogar todas as sessões de um usuário."""
    require_workspace_access(request.user, workspace_id)
    require_workspace_admin(request.user, workspace_id)

    workspace = Workspace.objects.get(pk=workspace_id)
    membership = get_object_or_404(WorkspaceMembership, workspace=workspace, user_id=user_id)
    target_user = membership.user
    _authorize_global_account_action(request.user, target_user, workspace_id)

    if target_user == request.user:
        messages.error(request, "Você não pode revogar suas próprias sessões.")
        return redirect("configuracoes-usuarios")

    # Django armazena sessão codificada/assinada; consulta textual nunca é confiável.
    deleted_count = revoke_db_sessions_for_user(target_user.pk)

    # Log do evento de revogação de sessões
    log_financial_operation(
        action="update",
        result="success",
        description=f"Todas as sessões revogadas para: '{target_user.username}' ({deleted_count} sessões)",
        workspace=workspace,
        profile=None,
        user=request.user,
        request=request,
        object_type="User",
        object_id=str(target_user.pk),
        object_repr=target_user.username,
        details={"revoked_sessions": deleted_count},
        ledger_batch_id="",
        result_status="success",
        severity="warning",
    )

    messages.success(request, f"Todas as sessões de '{target_user.username}' foram revogadas.")
    return redirect("configuracoes-usuarios")


@login_required
@require_http_methods(["GET", "POST"])
def grant_management(request, workspace_id, membership_id):
    """Gestão de permissões por perfil financeiro e módulo."""
    require_workspace_access(request.user, workspace_id)
    require_workspace_admin(request.user, workspace_id)

    workspace = Workspace.objects.get(pk=workspace_id)
    target_membership = WorkspaceMembership.objects.get(pk=membership_id, workspace=workspace)
    target_user = target_membership.user

    # Perfis do workspace
    profiles = FinancialProfile.objects.filter(workspace=workspace, is_archived=False)

    # Grants existentes
    grants = ProfileGrant.objects.filter(membership=target_membership).select_related("profile")
    grants_dict = {g.profile_id: g for g in grants}

    if request.method == "POST":
        # Os cinco níveis são a fonte da verdade. Os checkboxes de ação em massa
        # são controles de UX, não autorizações independentes.
        fields = (
            "overview_level", "accounts_level", "expenses_level",
            "investments_level", "movements_level",
        )
        allowed = set(ProfileGrant.Level.values)
        requested = []
        for profile in profiles:
            prefix = f"grant_{profile.pk}_"
            levels = {key: request.POST.get(f"{prefix}{key}", "") for key in fields}
            if any(value not in allowed for value in levels.values()):
                from django.http import HttpResponseBadRequest
                return HttpResponseBadRequest("Nível de permissão ausente ou inválido.")
            requested.append((profile, levels))
        # Não deixar perfil parcialmente atualizado se alguma gravação falhar.
        with transaction.atomic():
            for profile, levels in requested:
                ProfileGrant.objects.update_or_create(
                    membership=target_membership,
                    profile=profile,
                    defaults={
                        **levels,
                        "can_view": any(value != ProfileGrant.Level.NONE for value in levels.values()),
                        "can_edit": any(value == ProfileGrant.Level.EDIT for value in levels.values()),
                    },
                )
        messages.success(request, f"Permissões de '{target_user.username}' atualizadas.")
        return redirect("core:grant-management", workspace_id=workspace.pk, membership_id=membership_id)

    # Preparar dados para o template
    grant_data = []
    for profile in profiles:
        grant = grants_dict.get(profile.pk)
        levels = [getattr(grant, field) for field in (
            "overview_level", "accounts_level", "expenses_level",
            "investments_level", "movements_level",
        )] if grant else []
        grant_data.append({
            "profile": profile,
            "grant": grant,
            "all_view": bool(levels) and all(value != ProfileGrant.Level.NONE for value in levels),
            "all_edit": bool(levels) and all(value == ProfileGrant.Level.EDIT for value in levels),
        })

    return render(request, "core/grant_management.html", {
        "workspace": workspace,
        "target_user": target_user,
        "target_membership": target_membership,
        "grant_data": grant_data,
        "active_nav": "settings",
        "title": f"Permissões: {target_user.username}",
    })


@login_required
@require_http_methods(["POST"])
def user_delete_account(request, workspace_id, user_id):
    """Excluir credenciais e identidade pessoal mantendo registros financeiros e auditoria.

    O identificador interno do usuário permanece como referência auditável (tombstone).
    Não é exclusão física do registro: FKs PROTECT impedem apagar autores de lançamentos.
    """
    require_workspace_access(request.user, workspace_id)
    require_workspace_admin(request.user, workspace_id)
    if request.user.pk == user_id:
        raise PermissionDenied("Não é permitido excluir sua própria conta.")

    with transaction.atomic():
        member = get_object_or_404(
            WorkspaceMembership.objects.select_for_update().select_related("user", "workspace"),
            workspace_id=workspace_id, user_id=user_id,
        )
        target = get_user_model().objects.select_for_update().get(pk=member.user_id)
        if target.is_superuser:
            raise PermissionDenied("Exclusão de contas globais requer administração do sistema.")
        if WorkspaceMembership.objects.filter(user=target).exclude(pk=member.pk).exists():
            raise PermissionDenied("Esta conta também participa de outro núcleo. Remova primeiro os outros acessos com os respectivos administradores.")
        if member.role == WorkspaceMembership.Role.ADMIN and not WorkspaceMembership.objects.filter(
            workspace_id=workspace_id, role=WorkspaceMembership.Role.ADMIN,
            user__is_active=True,
        ).exclude(pk=member.pk).exists():
            raise PermissionDenied("Não é possível excluir o último administrador ativo.")
        # Confirmação no backend: JavaScript e caixas de diálogo podem ser contornados.
        if request.POST.get("confirm_username", "") != target.username or request.POST.get("confirmation") != "excluir":
            messages.error(request, "Confirme o nome exato da conta para excluí-la.")
            return redirect("core:user-edit", workspace_id=workspace_id, user_id=user_id)
        former_id = target.pk
        # Chave aleatória evita colisão e nunca reutiliza o nome antigo.
        target.username = f"excluido_{former_id}_{secrets.token_hex(6)}"
        target.first_name = ""
        target.last_name = ""
        target.email = ""
        target.is_active = False
        target.is_staff = False
        target.is_superuser = False
        target.set_unusable_password()
        target.save(update_fields=["username", "first_name", "last_name", "email", "is_active",
                                   "is_staff", "is_superuser", "password"])
        from apps.core.models import RecoveryCode, UserProfile
        RecoveryCode.objects.filter(user=target).delete()
        UserProfile.objects.filter(user=target).update(
            recovery_code_hash=None, recovery_code_version=0, recovery_code_created=None,
            recovery_acknowledged_at=None, theme="auto",
        )
        member.delete()  # revoga grants; lançamentos e logs financeiros usam o ID preservado
        revoked_count = revoke_db_sessions_for_user(target.pk)
        log_financial_operation(
            action="delete", result="success", workspace=member.workspace, profile=None,
            description=f"Identidade de usuário excluída por anonimização (id={former_id})",
            user=request.user, request=request, object_type="User", object_id=str(former_id),
            object_repr=f"Usuário excluído #{former_id}",
            details={"status": "anonymized", "identity_anonymized": True, "audit_references_preserved": True, "revoked_sessions": revoked_count},
            ledger_batch_id="", result_status="success", severity="warning",
        )
    messages.success(request, "Conta excluída e anonimizada. Registros financeiros e auditorias preservados.")
    return redirect("configuracoes-usuarios")


@login_required
@require_http_methods(["POST"])
def user_remove_access(request, workspace_id, user_id):
    """Remove membership without deleting financial/audit records or cross-workspace access."""
    require_workspace_admin(request.user, workspace_id)
    if request.user.pk == user_id:
        raise PermissionDenied("Não é permitido remover sua própria conta.")
    with transaction.atomic():
        membership = get_object_or_404(
            WorkspaceMembership.objects.select_for_update().select_related("user"),
            workspace_id=workspace_id, user_id=user_id)
        if membership.role == WorkspaceMembership.Role.ADMIN and not WorkspaceMembership.objects.filter(
            workspace_id=workspace_id, role=WorkspaceMembership.Role.ADMIN,
            user__is_active=True).exclude(pk=membership.pk).exists():
            raise PermissionDenied("Não é possível remover o último administrador ativo.")
        workspace = membership.workspace
        target = membership.user
        membership.delete()
        if not WorkspaceMembership.objects.filter(user=target).exists():
            target.is_active = False
            target.save(update_fields=["is_active"])
        log_financial_operation(action="delete", result="success",
            description=f"Acesso do usuário {target.username} removido do núcleo",
            workspace=workspace, profile=None, user=request.user, request=request,
            object_type="User", object_id=str(target.pk), object_repr=target.username,
            details={"account_preserved": True}, ledger_batch_id="",
            result_status="success", severity="warning")
    messages.success(request, "Acesso removido. Dados financeiros e auditorias preservados.")
    return redirect("configuracoes-usuarios")
