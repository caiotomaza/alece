# SPDX-License-Identifier: GPL-3.0-only
"""Context processors for ALECE."""


def privacy_mode(request):
    """Add privacy mode flag to template context based on session."""
    return {
        "privacy_mode": request.session.get("alece_privacy", False),
    }