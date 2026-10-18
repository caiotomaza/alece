# SPDX-License-Identifier: GPL-3.0-only
"""Authentication endpoints with offline, single-use recovery."""
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods

from apps.core.auth_services import (
    allow_auth_attempt,
    issue_recovery_code,
    redeem_recovery_code,
)


@never_cache
@sensitive_post_parameters("password")
@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST":
        if not allow_auth_attempt(request, "login", request.POST.get("username", "").strip()):
            messages.error(request, "Muitas tentativas. Tente novamente em 15 minutos.")
            return render(request, "auth/login.html", status=429)
        if form.is_valid():
            login(request, form.get_user())
            next_url = request.GET.get("next", "")
            if not url_has_allowed_host_and_scheme(
                next_url, {request.get_host()}, require_https=request.is_secure()
            ):
                next_url = reverse("home")
            return redirect(next_url)
        messages.error(request, "Usuário ou senha inválidos.")
    return render(request, "auth/login.html", {"form": form})


@require_http_methods(["POST"])
@login_required
def logout_view(request):
    logout(request)
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
            return render(request, "auth/password_change.html", status=429)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
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
            return render(request, "auth/recovery_use.html", status=429)
        success, errors = redeem_recovery_code(
            username, request.POST.get("code", "").strip(), request.POST)
        if success:
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
    if request.method == "POST":
        if not allow_auth_attempt(request, "recovery-generate", request.user.username):
            messages.error(request, "Muitas tentativas. Tente novamente em 15 minutos.")
            return render(request, "auth/recovery_generate.html", status=429)
        code = issue_recovery_code(request.user.pk, request.POST.get("current_password", ""))
        if code:
            return render(request, "auth/recovery_generate.html", {
                "code": code, "username": request.user.username,
            })
        messages.error(request, "Não foi possível gerar o código. Confira sua senha atual.")
    return render(request, "auth/recovery_generate.html")
