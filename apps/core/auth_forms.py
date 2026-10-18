# SPDX-License-Identifier: GPL-3.0-only
"""Admin login shares the public login attempt budget."""
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.exceptions import ValidationError

from apps.core.auth_services import allow_auth_attempt


class ThrottledAdminAuthenticationForm(AdminAuthenticationForm):
    def clean(self):
        username = self.cleaned_data.get("username", "")
        if not allow_auth_attempt(self.request, "login", username.strip()):
            raise ValidationError("Muitas tentativas. Tente novamente em 15 minutos.",
                                  code="too_many_attempts")
        return super().clean()
