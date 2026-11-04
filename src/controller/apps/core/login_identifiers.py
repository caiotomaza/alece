# SPDX-License-Identifier: GPL-3.0-only
"""Identificadores de login: usuário obrigatório; e-mail opcional e não ambíguo."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


def clean_login_email(email, *, exclude_pk=None, username=None):
    """Enforce case-insensitive uniqueness in application forms.

    The stock Django User email field is not UNIQUE in the DB. For legacy duplicate
    emails, login-by-email fails closed instead of choosing a random account.
    """
    normalized = (email or "").strip().lower()
    if not normalized:
        return ""
    users = get_user_model().objects
    if users.filter(email__iexact=normalized).exclude(pk=exclude_pk).exists():
        raise ValidationError("Este e-mail já está associado a outra conta.")
    if users.filter(username__iexact=normalized).exclude(pk=exclude_pk).exists():
        raise ValidationError("Este e-mail entra em conflito com um nome de usuário existente.")
    if username and normalized.casefold() == username.strip().casefold():
        # Same account, not an ambiguity.
        return normalized
    return normalized


def validate_login_username(username, *, exclude_pk=None):
    identifier = (username or "").strip()
    if get_user_model().objects.filter(email__iexact=identifier).exclude(pk=exclude_pk).exists():
        raise ValidationError("Este nome de usuário coincide com um e-mail cadastrado.")
    return identifier
