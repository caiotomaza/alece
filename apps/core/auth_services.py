# SPDX-License-Identifier: GPL-3.0-only
"""Offline recovery and shared, bounded authentication attempt windows."""
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from apps.core.models import AuthenticationAttempt, UserProfile


def allow_auth_attempt(request, scope, username):
    """Count account and peer attempts across workers; never trust forwarded IP headers.

    Counts successful requests too, preventing reset-based bypass. Expired windows
    reset under a row lock; stale rows are pruned after one day. Only keyed hashes
    of identifiers are persisted. Reverse proxies may share the peer quota.
    """
    now = timezone.now()
    AuthenticationAttempt.objects.filter(window_started__lt=now - timedelta(days=1)).delete()
    # Check the peer first so blocked username spraying cannot create new rows.
    identifiers = [("peer", request.META.get("REMOTE_ADDR", "unknown"), 60),
                   ("account", username.casefold(), 10)]
    with transaction.atomic():
        for kind, identifier, limit in identifiers:
            key = salted_hmac("alece.auth-attempt", f"{scope}:{kind}:{identifier}",
                              algorithm="sha256").hexdigest()
            bucket, _ = AuthenticationAttempt.objects.get_or_create(
                key=key, defaults={"window_started": now})
            bucket = AuthenticationAttempt.objects.select_for_update().get(pk=bucket.pk)
            if bucket.window_started <= now - timedelta(minutes=15):
                bucket.window_started = now
                bucket.attempts = 0
            if bucket.attempts >= limit:
                return False
            bucket.attempts += 1
            bucket.save(update_fields=["attempts", "window_started"])
    return True


@transaction.atomic
def issue_recovery_code(user_id, password):
    user = get_user_model().objects.select_for_update().get(pk=user_id)
    if not user.is_active or not user.check_password(password):
        return None
    code = secrets.token_urlsafe(24)  # 192 bits from the OS CSPRNG.
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.set_recovery_code(code)
    return code


@transaction.atomic
def redeem_recovery_code(username, code, password_data):
    """Lock the same user row as issuance before reading/consuming the code."""
    user = get_user_model().objects.select_for_update().filter(
        username=username, is_active=True).first()
    profile = UserProfile.objects.filter(user=user).first() if user else None
    if not profile or not profile.verify_recovery_code(code):
        return False, ["Código de recuperação inválido."]
    form = SetPasswordForm(user, password_data)
    if not form.is_valid():
        return False, [error for errors in form.errors.values() for error in errors]
    form.save()
    profile.clear_recovery_code()
    return True, []
