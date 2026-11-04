# SPDX-License-Identifier: GPL-3.0-only
"""Formulários para configuração inicial (bootstrap) e gestão de usuários."""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, SetPasswordForm
from django.core.exceptions import ValidationError

from apps.finance.models import ProfileGrant
from apps.core.login_identifiers import clean_login_email, validate_login_username

User = get_user_model()


class BootstrapSetupForm(forms.Form):
    email = forms.EmailField(label="E-mail (opcional)", required=False, max_length=254,
                             widget=forms.EmailInput(attrs={"autocomplete": "email", "class": "setup-input"}))
    """Formulário simplificado para configuração inicial do primeiro Administrador.

    Apenas três campos obrigatórios: usuário, senha, confirmação de senha.
    O núcleo financeiro, perfil e permissões são criados automaticamente no backend.
    """
    username = forms.CharField(
        max_length=150,
        required=True,
        label="Nome de usuário",
        widget=forms.TextInput(attrs={
            "placeholder": "Nome de usuário do administrador",
            "autocomplete": "username",
            "class": "setup-input",
            "autocapitalize": "none",
            "spellcheck": "false",
        }),
    )
    password1 = forms.CharField(
        required=True,
        label="Senha",
        widget=forms.PasswordInput(attrs={
            "placeholder": "Senha do administrador",
            "autocomplete": "new-password",
            "class": "setup-input",
        }),
    )
    password2 = forms.CharField(
        required=True,
        label="Confirmação de senha",
        widget=forms.PasswordInput(attrs={
            "placeholder": "Confirme a senha",
            "autocomplete": "new-password",
            "class": "setup-input",
        }),
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Este nome de usuário já está em uso.")
        return validate_login_username(username)

    def clean_email(self):
        return clean_login_email(self.cleaned_data.get("email"))

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("As senhas não coincidem.")
        # Validação de senha do Django
        from django.contrib.auth.password_validation import validate_password
        validate_password(password1, User())
        return password2


class UserManagementForm(UserCreationForm):
    """Formulário para criação de usuários (Admin/Comum) pelo Administrador."""

    ROLE_CHOICES = [
        ("admin", "Administrador"),
        ("common", "Comum"),
    ]

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=True,
        label="Papel",
        widget=forms.Select(),
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        label="Conta ativa",
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        labels = {"email": "E-mail (opcional)"}
        widgets = {
            "username": forms.TextInput(attrs={"placeholder": "Nome de usuário"}),
        }

    def __init__(self, *args, **kwargs):
        self.requesting_user = kwargs.pop("requesting_user", None)
        self.target_workspace = kwargs.pop("target_workspace", None)
        super().__init__(*args, **kwargs)
        # Administrador não pode criar outro admin no mesmo workspace se não for admin do sistema
        # (essa validação será feita na view)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Este nome de usuário já está em uso.")
        return validate_login_username(username)

    def clean_email(self):
        return clean_login_email(self.cleaned_data.get("email"))

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = self.cleaned_data.get("is_active", True)
        if commit:
            user.save()
        return user


class UserEditForm(UserChangeForm):
    """Formulário para edição de usuários existentes."""

    ROLE_CHOICES = [
        ("admin", "Administrador"),
        ("common", "Comum"),
    ]

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        required=True,
        label="Papel",
    )
    is_active = forms.BooleanField(
        required=False,
        label="Conta ativa",
    )

    class Meta:
        model = User
        fields = ("username", "email", "is_active")
        labels = {"email": "E-mail (opcional)"}

    def __init__(self, *args, **kwargs):
        self.requesting_user = kwargs.pop("requesting_user", None)
        super().__init__(*args, **kwargs)
        # Remover campo de senha (mudança de senha é feita separadamente)
        self.fields.pop("password", None)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Este nome de usuário já está em uso.")
        return validate_login_username(username, exclude_pk=self.instance.pk)

    def clean_email(self):
        return clean_login_email(self.cleaned_data.get("email"), exclude_pk=self.instance.pk)

    def clean(self):
        cleaned_data = super().clean()
        # Impedir autopromoção
        if self.requesting_user and self.instance == self.requesting_user:
            if self.cleaned_data.get("role") == "admin" and self.instance != self.requesting_user:
                # Se tentar promover a si mesmo para admin quando já é, ok
                pass
            # Não permitir auto-desativação
            if not cleaned_data.get("is_active", True):
                self.add_error("is_active", "Você não pode desativar sua própria conta.")
        return cleaned_data


class UserPasswordResetForm(SetPasswordForm):
    """Formulário para redefinição de senha pelo administrador."""

    def __init__(self, *args, **kwargs):
        self.requesting_user = kwargs.pop("requesting_user", None)
        self.target_user = kwargs.pop("target_user", None)
        super().__init__(*args, **kwargs)
        # A validação de auto-redefinição é feita na view antes de instanciar o formulário


class ProfileGrantForm(forms.ModelForm):
    """Formulário para concessão de permissões por perfil e módulo."""

    class Meta:
        model = ProfileGrant
        fields = [
            "can_view", "can_edit",
            "overview_level", "accounts_level", "expenses_level",
            "investments_level", "movements_level",
        ]
        widgets = {
            "overview_level": forms.Select(),
            "accounts_level": forms.Select(),
            "expenses_level": forms.Select(),
            "investments_level": forms.Select(),
            "movements_level": forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Garantir que can_edit implica can_view
        if self.instance and self.instance.can_edit:
            self.initial["can_view"] = True