# SPDX-License-Identifier: GPL-3.0-only
"""Authenticate by existing username or optional unambiguous email.

Delegates password hashing, authentication checks and inactive accounts to Django.
"""
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm


class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label="Usuário ou e-mail", max_length=254,
                               widget=forms.TextInput(attrs={
                                   "autocomplete": "username", "autocapitalize": "none",
                                   "spellcheck": "false", "autofocus": True}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs["maxlength"] = "254"

    def clean(self):
        # Django's AuthenticationForm still invokes authenticate() with the canonical
        # username, so password checks, rate limits, session setup and is_active
        # protection remain delegated to the configured backend.
        identifier = (self.cleaned_data.get("username") or "").strip()
        if identifier:
            users = get_user_model().objects
            matches = list(users.filter(username__iexact=identifier).values_list("username", "pk")[:2])
            emails = (list(users.filter(email__iexact=identifier).exclude(email="")
                           .values_list("username", "pk")[:2]) if "@" in identifier else [])
            candidates = {pk: username for username, pk in (matches + emails)}
            if len(candidates) == 1 and len(matches) <= 1 and len(emails) <= 1:
                self.cleaned_data["username"] = next(iter(candidates.values()))
            elif len(matches) > 1 or len(emails) > 1 or len(candidates) > 1:
                raise self.get_invalid_login_error()
        return super().clean()
