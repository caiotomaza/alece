# SPDX-License-Identifier: GPL-3.0-only
"""Authentication endpoints with offline, single-use recovery."""
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from apps.core.login_forms import EmailOrUsernameAuthenticationForm
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods
import secrets

from apps.core.auth_services import (
    allow_auth_attempt,
    issue_recovery_codes,
    redeem_recovery_code,
)
from apps.finance.services.system_log import log_financial_operation, log_error_event


@never_cache
@sensitive_post_parameters("password")
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = EmailOrUsernameAuthenticationForm(request, data=request.POST or None)
    if request.method == "POST":
        if not allow_auth_attempt(request, "login", request.POST.get("username", "").strip()):
            messages.error(request, "Muitas tentativas. Tente novamente em 15 minutos.")
            return render(request, "auth/login.html", status=429)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Log do evento de login
            log_financial_operation(
                action="login",
                result="success",
                description=f"Login bem-sucedido: {user.username}",
                workspace=None,
                profile=None,
                user=user,
                request=request,
                object_type="User",
                object_id=str(user.pk),
                object_repr=user.username,
                details={},
                ledger_batch_id="",
                result_status="success",
                severity="info",
            )

            next_url = request.GET.get("next", "")
            if not url_has_allowed_host_and_scheme(
                next_url, {request.get_host()}, require_https=request.is_secure()
            ):
                next_url = reverse("home")
            return redirect(next_url)
        else:
            # Log de tentativa de login falha
            username = request.POST.get("username", "").strip()
            log_error_event(
                module="auth",
                action="login",
                description="Tentativa de login falhou (identificador omitido)",
                request=request,
                error_message="Credenciais inválidas",
                severity="warning",
            )
            messages.error(request, "Usuário ou senha inválidos.")
    return render(request, "auth/login.html", {"form": form})


@require_http_methods(["POST"])
@login_required
def logout_view(request):
    user = request.user
    username = user.username
    logout(request)

    # Log do evento de logout
    log_financial_operation(
        action="logout",
        result="success",
        description=f"Logout: {username}",
        workspace=None,
        profile=None,
        user=user,
        request=request,
        object_type="User",
        object_id=str(user.pk),
        object_repr=username,
        details={},
        ledger_batch_id="",
        result_status="success",
        severity="info",
    )

    messages.info(request, "Você saiu do sistema.")
    return redirect("login")


@never_cache
@sensitive_post_parameters("old_password", "new_password1", "new_password2")
@require_http_methods(["GET", "POST"])
@login_required
def password_change_view(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST":
        if not allow_auth_attempt(request, "password-change", request.user.username):
            messages.error(request, "Muitas tentativas. Tente novamente em 15 minutos.")
            return render(request, "auth/password_change.html", {"form": form}, status=429)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)

            # Log do evento de mudança de senha
            log_financial_operation(
                action="update",
                result="success",
                description=f"Senha alterada pelo próprio usuário: {user.username}",
                workspace=None,
                profile=None,
                user=user,
                request=request,
                object_type="User",
                object_id=str(user.pk),
                object_repr=user.username,
                details={},
                ledger_batch_id="",
                result_status="success",
                severity="info",
            )

            messages.success(request, "Senha alterada com sucesso.")
            return redirect("home")
        messages.error(request, "Corrija os erros abaixo.")
    return render(request, "auth/password_change.html", {"form": form})


@never_cache
@require_http_methods(["GET", "POST"])
def recovery_code_request_view(request):
    # The old URL remains informative only: knowing a username grants no issuance.
    return render(request, "auth/recovery_request.html")


@never_cache
@sensitive_post_parameters("code", "new_password1", "new_password2")
@require_http_methods(["GET", "POST"])
def recovery_code_use_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        if not allow_auth_attempt(request, "recovery-use", username):
            messages.error(request, "Muitas tentativas. Tente novamente em 15 minutos.")
            return render(request, "auth/recovery_use.html", {}, status=429)
        success, errors = redeem_recovery_code(
            username, request.POST.get("code", "").strip(), request.POST)
        if success:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.filter(username=username).first()

            # Log do evento de recuperação
            log_financial_operation(
                action="update",
                result="success",
                description=f"Senha redefinida via código de recuperação: {username}",
                workspace=None,
                profile=None,
                user=user,
                request=request,
                object_type="User",
                object_id=str(user.pk) if user else "",
                object_repr=username,
                details={"method": "recovery_code"},
                ledger_batch_id="",
                result_status="success",
                severity="warning",
            )

            messages.success(request, "Senha redefinida com sucesso. Faça login com a nova senha.")
            return redirect("login")
        for error in errors:
            messages.error(request, error)
    return render(request, "auth/recovery_use.html")



@never_cache
@sensitive_post_parameters("current_password")
@login_required
@require_http_methods(["GET", "POST"])
def recovery_code_generate_view(request):
    """Authenticated reset: require current password; render one-time codes in the modal."""
    if request.method == "POST":
        if not allow_auth_attempt(request, "recovery-generate", request.user.username):
            messages.error(request, "Muitas tentativas. Tente novamente em 15 minutos.")
            return render(request, "auth/recovery_generate.html", status=429)
        codes = issue_recovery_codes(request.user.pk, request.POST.get("current_password", ""))
        if codes:
            request.session["alece_recovery_nonce"] = secrets.token_urlsafe(32)
            log_financial_operation(
                action="create", result="success", description="Conjunto de recuperação substituído",
                workspace=None, profile=None, user=request.user, request=request,
                object_type="User", object_id=str(request.user.pk), object_repr=request.user.username,
                details={"codes_issued": 6}, ledger_batch_id="", result_status="success", severity="warning",
            )
            return render(request, "core/recovery_status.html", {
                "codes": codes, "recovery_count": 6,
                "nonce": request.session["alece_recovery_nonce"],
            })
        messages.error(request, "Senha atual incorreta. Nenhum código foi alterado.")
    return render(request, "auth/recovery_generate.html")
