# SPDX-License-Identifier: GPL-3.0-only
"""Resolve a preferência apenas entre perfis já autorizados para a navegação."""
from django import template
from apps.finance.profile_selection import selected_profile_id

register = template.Library()


@register.simple_tag(takes_context=True)
def accessible_navigation_profiles(context):
    """Lista de perfis no menu também em formulários CRUD sem nav_profiles.

    O menu nunca escolhe implicitamente um perfil nem amplia concessões.
    """
    cached = context.get("nav_profiles")
    if cached is not None:
        return cached
    request = context.get("request")
    workspace = context.get("workspace")
    if not request or not workspace or not request.user.is_authenticated:
        return []
    from apps.core.permissions import get_accessible_profiles
    return list(get_accessible_profiles(request.user).filter(
        workspace=workspace, is_archived=False,
    ).order_by("pk"))


@register.simple_tag(takes_context=True)
def selected_financial_profile(context):
    request = context.get("request")
    workspace = context.get("workspace")
    if not request or not workspace or not request.user.is_authenticated:
        return None
    chosen = selected_profile_id(request, workspace.pk)
    if chosen is None:
        return None
    for profile in context.get("displayed_nav_profiles") or accessible_navigation_profiles(context):
        if profile.pk == chosen and not profile.is_archived and profile.deleted_at is None:
            return profile
    return None
