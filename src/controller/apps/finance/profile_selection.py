# SPDX-License-Identifier: GPL-3.0-only
"""Preferência de perfil da navegação, validada pelo servidor em cada requisição.

Não concede permissões. A sessão é apenas uma preferência; o acesso real aos
módulos continua submetido a get_module_profiles/user_can_module.
"""
SESSION_KEY = "alece_selected_financial_profile_v1"


def selected_profile_id(request, workspace_id):
    preference = request.session.get(SESSION_KEY)
    if (not isinstance(preference, dict) or
            preference.get("user_id") != request.user.pk or
            preference.get("workspace_id") != workspace_id):
        return None
    candidate = preference.get("profile_id")
    return candidate if type(candidate) is int and candidate > 0 else None


def remember_profile(request, workspace_id, profile_id):
    if profile_id is None:
        request.session.pop(SESSION_KEY, None)
    else:
        request.session[SESSION_KEY] = {
            "user_id": request.user.pk,
            "workspace_id": workspace_id,
            "profile_id": profile_id,
        }
