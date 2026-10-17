# SPDX-License-Identifier: GPL-3.0-only
"""Views de autenticação e recuperação offline.
Login por usuário/senha, logout, alteração de senha e código de recuperação único.
"""
import hashlib
import secrets
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.core.models import UserProfile
from apps.finance.models import WorkspaceMembership


def get_user_workspaces(user):
    """Retorna workspaces onde o usuário tem membership ativo."""
    return WorkspaceMembership.objects.filter(user=user).select_related("workspace")


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Login com usuário/senha. Redireciona para home se já autenticado."""
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "Login realizado com sucesso.")
            next_url = request.GET.get("next") or reverse("home")
            return HttpResponseRedirect(next_url)
        else:
            messages.error(request, "Usuário ou senha inválidos.")
    else:
        form = AuthenticationForm(request)

    return render(request, "auth/login.html", {"form": form})


@require_http_methods(["POST"])
@login_required
def logout_view(request):
    """Logout do usuário autenticado."""
    logout(request)
    messages.info(request, "Você saiu do sistema.")
    return redirect("login")


@require_http_methods(["GET", "POST"])
@login_required
def password_change_view(request):
    """Alteração de senha do usuário autenticado."""
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Senha alterada com sucesso.")
            return redirect("home")
        else:
            messages.error(request, "Corrija os erros abaixo.")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "auth/password_change.html", {"form": form})


def generate_recovery_code() -> str:
    """Gera um código de recuperação seguro (32 caracteres URL-safe)."""
    return secrets.token_urlsafe(24)


@transaction.atomic
@require_http_methods(["GET", "POST"])
def recovery_code_request_view(request):
    """
    Solicita código de recuperação offline.
    O código é exibido uma única vez e deve ser guardado pelo usuário.
    Não há envio por e-mail; é responsabilidade do usuário armazenar o código.
    """
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        if not username:
            messages.error(request, "Informe o nome de usuário.")
            return render(request, "auth/recovery_request.html")

        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Não revelar se o usuário existe
            messages.success(request, "Se o usuário existir, um código de recuperação será gerado.")
            return render(request, "auth/recovery_request.html")

        # Gerar e armazenar código de recuperação (hash)
        code = generate_recovery_code()
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.recovery_code_hash = hashlib.sha256(code.encode()).hexdigest()
        profile.recovery_code_created = timezone.now()
        profile.save(update_fields=["recovery_code_hash", "recovery_code_created", "updated_at"])

        # Exibir código apenas uma vez
        return render(request, "auth/recovery_request.html", {
            "code": code,
            "username": username,
        })

    return render(request, "auth/recovery_request.html")


@transaction.atomic
@require_http_methods(["GET", "POST"])
def recovery_code_use_view(request):
    """
    Usa o código de recuperação para definir nova senha.
    O código só pode ser usado uma vez e expira após uso.
    """
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        code = request.POST.get("code", "").strip()
        new_password1 = request.POST.get("new_password1", "")
        new_password2 = request.POST.get("new_password2", "")

        if not all([username, code, new_password1, new_password2]):
            messages.error(request, "Preencha todos os campos.")
            return render(request, "auth/recovery_use.html")

        if new_password1 != new_password2:
            messages.error(request, "As senhas não coincidem.")
            return render(request, "auth/recovery_use.html")

        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, "Código de recuperação inválido.")
            return render(request, "auth/recovery_use.html")

        # Verificar código via UserProfile
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            messages.error(request, "Nenhum código de recuperação ativo para este usuário.")
            return render(request, "auth/recovery_use.html")

        if not profile.recovery_code_hash:
            messages.error(request, "Nenhum código de recuperação ativo para este usuário.")
            return render(request, "auth/recovery_use.html")

        code_hash = hashlib.sha256(code.encode()).hexdigest()
        if code_hash != profile.recovery_code_hash:
            messages.error(request, "Código de recuperação inválido.")
            return render(request, "auth/recovery_use.html")

        # Código válido - definir nova senha e invalidar código
        user.set_password(new_password1)
        user.save(update_fields=["password"])
        profile.clear_recovery_code()

        messages.success(request, "Senha redefinida com sucesso. Faça login com a nova senha.")
        return redirect("login")

    return render(request, "auth/recovery_use.html")


@login_required
@require_http_methods(["GET", "POST"])
def recovery_code_generate_view(request):
    """
    Gera novo código de recuperação para o usuário autenticado.
    Invalida código anterior se existir.
    """
    if request.method == "POST":
        code = generate_recovery_code()
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        profile.recovery_code_hash = hashlib.sha256(code.encode()).hexdigest()
        profile.recovery_code_created = timezone.now()
        profile.save(update_fields=["recovery_code_hash", "recovery_code_created", "updated_at"])

        return render(request, "auth/recovery_generate.html", {
            "code": code,
            "username": request.user.username,
        })

    return render(request, "auth/recovery_generate.html")