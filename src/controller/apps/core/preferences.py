# SPDX-License-Identifier: GPL-3.0-only
"""Preferências leves por usuário, sem expor dados de outro núcleo."""
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache

from apps.core.models import UserProfile


@never_cache
@login_required
@require_POST
def set_theme_preference(request):
    choice = request.POST.get('theme')
    if choice not in {'light', 'dark'}:
        return JsonResponse({'error': 'Tema inválido.'}, status=400)
    with transaction.atomic():
        UserProfile.objects.update_or_create(user=request.user, defaults={'theme': choice})
    response = JsonResponse({'theme': choice})
    response.set_cookie(
        'alece_theme', choice, max_age=60 * 60 * 24 * 365,
        secure=request.is_secure(), httponly=False, samesite='Lax', path='/',
    )
    return response
