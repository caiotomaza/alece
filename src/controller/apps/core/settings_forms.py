# SPDX-License-Identifier: GPL-3.0-only
"""Forms for personal account settings and opt-in AI providers."""
import ipaddress
import re
from urllib.parse import urlsplit

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.core.models import AIProviderConfig
from apps.core.login_identifiers import clean_login_email, validate_login_username

User = get_user_model()


class PersonalInformationForm(forms.ModelForm):
    current_password = forms.CharField(
        label="Senha atual para confirmar a alteração", widget=forms.PasswordInput(render_value=False)
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email")
        labels = {"username": "Usuário", "first_name": "Nome", "last_name": "Sobrenome", "email": "E-mail"}

    def clean_current_password(self):
        value = self.cleaned_data["current_password"]
        if not self.instance.check_password(value):
            raise ValidationError("Senha atual incorreta.")
        return value

    def clean_username(self):
        name = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=name).exclude(pk=self.instance.pk).exists():
            raise ValidationError("Nome de usuário indisponível.")
        return validate_login_username(name, exclude_pk=self.instance.pk)

    def clean_email(self):
        return clean_login_email(self.cleaned_data.get("email"), exclude_pk=self.instance.pk)


class AIProviderConfigForm(forms.Form):
    """Presets pinados no servidor; edição livre somente para integração personalizada."""
    provider_type = forms.ChoiceField(label="Provedor de IA")
    provider_name = forms.CharField(label="Nome da integração", required=False, max_length=100)
    endpoint = forms.URLField(label="Endpoint HTTPS (Chat Completions compatível)", required=False, max_length=500)
    model_name = forms.CharField(label="Modelo", required=False, max_length=120)
    enabled = forms.BooleanField(label="Integração em uso", required=False,
                                 help_text="Somente uma API pode ficar ativa por núcleo financeiro.")
    api_token = forms.CharField(label="Chave da API (token / API key)", required=False,
                                max_length=4096, strip=True,
                                widget=forms.PasswordInput(render_value=False,
                                                           attrs={"autocomplete": "new-password", "placeholder": "Cole sua chave da API"}))

    def __init__(self, *args, instance=None, has_active_provider=False, **kwargs):
        from apps.core.ai_catalog import PROVIDERS, get_preset_code
        from apps.core.ai_credentials import has_token
        self.instance = instance
        self.previous_code = (get_preset_code(instance.endpoint) or "custom") if instance else None
        self.has_existing_token = bool(instance and (has_token(instance.pk) or instance.api_key_env))
        initial = dict(kwargs.pop("initial", {}))
        code = self.previous_code or "openai"
        initial.setdefault("provider_type", code)
        if instance:
            initial.setdefault("provider_name", instance.name)
            initial.setdefault("endpoint", instance.endpoint)
            initial.setdefault("model_name", instance.model_name)
            initial.setdefault("enabled", instance.enabled)
        else:
            preset = PROVIDERS[code]
            initial.setdefault("provider_name", preset["name"])
            initial.setdefault("endpoint", preset["endpoint"])
            initial.setdefault("model_name", preset["model"])
            initial.setdefault("enabled", not has_active_provider)
        super().__init__(*args, initial=initial, **kwargs)
        self.fields["provider_type"].choices = [
            (key, entry["name"]) for key, entry in PROVIDERS.items()
        ] + [("custom", "Personalizada")]
        self.fields["provider_type"].widget.attrs["data-ai-provider-select"] = "1"
        for name in ("provider_name", "endpoint", "model_name"):
            self.fields[name].widget.attrs["data-ai-custom-field"] = "1"
        self.fields["enabled"].widget.attrs["data-ai-active-switch"] = "1"
        self.fields["api_token"].help_text = (
            "Deixe em branco para manter a chave existente." if self.has_existing_token
            else "A chave será armazenada no volume privado, nunca no banco de dados."
        )
        self.fields["endpoint"].help_text = "Para endpoints personalizados, autorize o host em ALECE_AI_ALLOWED_HOSTS."

    def clean(self):
        from apps.core.ai_catalog import PROVIDERS
        data = super().clean()
        code = data.get("provider_type")
        if not code:
            return data
        if code in PROVIDERS:
            preset = PROVIDERS[code]
            # Dados de preset sempre vêm do catálogo confiável, não do POST.
            data["provider_name"] = preset["name"]
            data["endpoint"] = preset["endpoint"]
            data["model_name"] = preset["model"]
        elif code == "custom":
            for key, label in (("provider_name", "nome"), ("endpoint", "endpoint HTTPS"), ("model_name", "modelo")):
                if not data.get(key):
                    self.add_error(key, f"Informe {label} para a integração personalizada.")
            endpoint = data.get("endpoint")
            if endpoint and not endpoint.startswith("https://"):
                self.add_error("endpoint", "O endpoint personalizado deve usar HTTPS.")
        else:
            self.add_error("provider_type", "Provedor inválido.")
        previous_endpoint = self.instance.endpoint if self.instance else None
        new_endpoint = data.get("endpoint")
        if not data.get("api_token") and (not self.has_existing_token or previous_endpoint != new_endpoint):
            self.add_error("api_token", "Informe a chave de API para este provedor ou endpoint.")
        return data
