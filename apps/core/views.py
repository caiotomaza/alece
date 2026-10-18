# SPDX-License-Identifier: GPL-3.0-only
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.core.permissions import get_user_workspace_memberships


@require_GET
@login_required
def index(request):
    return render(request, "index.html", {
        "memberships": get_user_workspace_memberships(request.user).order_by("workspace_id"),
    })


@require_GET
def live(request):
    return JsonResponse({"status": "alive"})


@require_GET
def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ready"})
