# SPDX-License-Identifier: GPL-3.0-only
"""Revogação real de sessões Django armazenadas no banco, sem expor conteúdo.

Session.session_data é codificado/assinado, não é JSON consultável com SQL LIKE.
A implantação atual usa django.contrib.sessions.backends.db (padrão do Django).
"""
from django.contrib.sessions.models import Session
from django.utils import timezone


def revoke_db_sessions_for_user(user_id):
    """Apaga sessões válidas de um usuário por ID exato, preservando outros usuários.

    Falha explicitamente para um backend não suportado, em vez de prometer revogação.
    """
    from django.conf import settings
    engine = settings.SESSION_ENGINE
    if engine != "django.contrib.sessions.backends.db":
        raise RuntimeError("Revogação requer backend de sessão DB; configure procedimento compatível.")
    target = str(user_id)
    keys = []
    total = 0
    for entry in Session.objects.filter(expire_date__gt=timezone.now()).iterator(chunk_size=500):
        decoded = entry.get_decoded()
        if isinstance(decoded, dict) and str(decoded.get("_auth_user_id", "")) == target:
            keys.append(entry.session_key)
            if len(keys) >= 200:
                total += Session.objects.filter(session_key__in=keys).delete()[0]
                keys.clear()
    if keys:
        total += Session.objects.filter(session_key__in=keys).delete()[0]
    return total
