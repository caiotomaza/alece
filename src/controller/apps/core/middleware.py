# SPDX-License-Identifier: GPL-3.0-only
"""First-run routing. Uninitialized public bindings fail closed."""
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect

from apps.core.bootstrap import is_system_initialized, setup_is_host_bound


class SystemInitializationMiddleware:
    EXEMPT_PREFIXES = ("/saude/", "/health/live/", "/health/ready/", "/healthz/", "/static/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        if path.startswith(self.EXEMPT_PREFIXES):
            return self.get_response(request)
        try:
            initialized = is_system_initialized()
        except Exception:
            # O proprio erro nao deve consultar o banco novamente.
            from apps.core.error_views import _render_error
            return _render_error(request, 503)

        if path.startswith(("/setup/", "/configuracao-inicial/")):
            if initialized:
                return redirect("login")
            if not setup_is_host_bound():
                return HttpResponseForbidden("Primeira configuração exige acesso local ao host.")
            return self.get_response(request)
        if not initialized:
            if setup_is_host_bound():
                return redirect("setup")
            from apps.core.error_views import _render_error
            return _render_error(request, 503)
        return self.get_response(request)


class RecoveryEnrollmentMiddleware:
    """Fail closed for signed-in accounts until codes have been stored and acknowledged."""
    EXEMPT = (
        "/configuracoes/codigos/", "/recovery/generate/", "/logout/",
        "/health/", "/saude/", "/healthz/", "/static/", "/media/", "/login/", "/entrar/",
        "/recovery/", "/recuperacao/", "/setup/", "/configuracao-inicial/", "/sair/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.conf import settings
        if not getattr(settings, "ALECE_REQUIRE_RECOVERY_SETUP", True):
            return self.get_response(request)
        if request.user.is_authenticated and not request.path_info.startswith(self.EXEMPT):
            from apps.core.models import RecoveryCode, UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            if (profile.recovery_acknowledged_at is None
                    or not RecoveryCode.objects.filter(user_id=request.user.pk, used_at__isnull=True).exists()):
                return redirect("configuracoes-codigos")
        return self.get_response(request)
