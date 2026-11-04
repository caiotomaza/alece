# SPDX-License-Identifier: GPL-3.0-only
"""Offline recovery and shared, bounded authentication attempt windows."""
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from apps.core.models import AuthenticationAttempt, UserProfile, RecoveryCode


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


RECOVERY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
RECOVERY_COUNT = 6
RECOVERY_LENGTH = 8


def recovery_digest(user_id, code):
    # Keyed hash makes offline dictionary attacks on 40-bit codes impractical without SECRET_KEY.
    return salted_hmac("alece.recovery.v2", f"{user_id}:{code}", algorithm="sha256").hexdigest()


@transaction.atomic
def issue_recovery_codes(user_id, password=None, *, onboarding=False):
    """Mint exactly six single-use codes after reauthentication, except first onboarding."""
    user = get_user_model().objects.select_for_update().get(pk=user_id)
    if not user.is_active:
        return None
    if not onboarding and (password is None or not user.check_password(password)):
        return None
    profile, _ = UserProfile.objects.select_for_update().get_or_create(user=user)
    if onboarding and (profile.recovery_acknowledged_at is not None or
                       RecoveryCode.objects.filter(user=user).exists()):
        return None
    codes = []
    while len(codes) < RECOVERY_COUNT:
        code = "".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(RECOVERY_LENGTH))
        if code not in codes:
            codes.append(code)
    RecoveryCode.objects.filter(user=user).delete()
    RecoveryCode.objects.bulk_create([
        RecoveryCode(user=user, slot=i, code_hash=recovery_digest(user.pk, code))
        for i, code in enumerate(codes)
    ])
    # Revoke any previous legacy code too. Never expose it again.
    profile.recovery_code_hash = None
    profile.recovery_code_version = 0
    profile.recovery_code_created = timezone.now()
    profile.recovery_acknowledged_at = None
    profile.save(update_fields=["recovery_code_hash", "recovery_code_version",
                                "recovery_code_created", "recovery_acknowledged_at", "updated_at"])
    return codes


@transaction.atomic
def acknowledge_recovery_codes(user_id):
    user = get_user_model().objects.select_for_update().get(pk=user_id)
    profile = UserProfile.objects.select_for_update().get(user=user)
    if RecoveryCode.objects.filter(user=user).count() != RECOVERY_COUNT:
        return False
    profile.recovery_acknowledged_at = timezone.now()
    profile.save(update_fields=["recovery_acknowledged_at", "updated_at"])
    return True


@transaction.atomic
def redeem_recovery_code(username, code, password_data):
    """Consume only the submitted code; leave the other five available."""
    user = get_user_model().objects.select_for_update().filter(
        username=username, is_active=True).first()
    if not user:
        return False, ["Código de recuperação inválido."]
    normalized = code.strip().upper().replace("-", "")
    matched = None
    if len(normalized) == RECOVERY_LENGTH and all(c in RECOVERY_ALPHABET for c in normalized):
        digest = recovery_digest(user.pk, normalized)
        from django.utils.crypto import constant_time_compare
        for candidate in RecoveryCode.objects.filter(user=user, used_at__isnull=True):
            if constant_time_compare(digest, candidate.code_hash):
                matched = candidate
    profile = UserProfile.objects.filter(user=user).first()
    legacy_ok = bool(profile and profile.recovery_code_version == 1 and
                     profile.verify_recovery_code(code)) if matched is None else False
    if matched is None and not legacy_ok:
        return False, ["Código de recuperação inválido."]
    form = SetPasswordForm(user, password_data)
    if not form.is_valid():
        return False, [error for errors in form.errors.values() for error in errors]
    form.save()
    if matched is not None:
        matched.used_at = timezone.now()
        matched.save(update_fields=["used_at"])
    else:
        profile.clear_recovery_code()
    return True, []
