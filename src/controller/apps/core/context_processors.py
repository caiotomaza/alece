# SPDX-License-Identifier: GPL-3.0-only
"""Context processors for ALECE."""


def privacy_mode(request):
    """Add privacy mode flag to template context based on session."""
    return {
        "privacy_mode": request.session.get("alece_privacy", False),
    }


def ui_theme(request):
    """DB is authoritative per account; cookie is only an anonymous fallback."""
    if getattr(request.user, 'is_authenticated', False):
        from apps.core.models import UserProfile
        choice = UserProfile.objects.filter(user_id=request.user.pk).values_list('theme', flat=True).first()
        theme = 'dark' if choice == 'dark' else 'light'
    else:
        theme = 'dark' if request.COOKIES.get('alece_theme') == 'dark' else 'light'
    return {'ui_theme': theme}
