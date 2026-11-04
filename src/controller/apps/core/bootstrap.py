# SPDX-License-Identifier: GPL-3.0-only
"""Atomic first-run setup. The Docker host binding is the trust boundary."""
from ipaddress import ip_address

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, transaction

from apps.core.models import UserProfile
from apps.finance.models import FinancialProfile, ProfileGrant, Workspace, WorkspaceMembership
from apps.finance.services.system_log import log_system_event


def is_system_initialized():
    """Legacy installations with any user must never reopen first-run setup."""
    return get_user_model().objects.exists()


def setup_is_host_bound():
    """Do not infer the original client from Docker NAT or forwarded headers."""
    try:
        return ip_address(settings.ALECE_BIND_IP).is_loopback
    except ValueError:
        return False


@transaction.atomic
def create_initial_admin(*, username, password, email=""):
    """Serialize competing setup requests before checking the empty database."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [1234567890])
    if is_system_initialized():
        raise ValidationError("O sistema já foi inicializado.")

    user = get_user_model().objects.create_user(
        username=username, password=password, email=email, is_staff=False, is_superuser=False,
    )
    UserProfile.objects.get_or_create(user=user)
    workspace = Workspace.objects.create(name="Pessoal", created_by=user)
    membership = WorkspaceMembership.objects.create(
        workspace=workspace, user=user, role=WorkspaceMembership.Role.ADMIN,
    )
    profile = FinancialProfile.objects.create(
        workspace=workspace, name="Principal", monthly_income=None,
    )
    ProfileGrant.objects.create(
        membership=membership, profile=profile, can_view=True, can_edit=True,
        overview_level=ProfileGrant.Level.EDIT,
        accounts_level=ProfileGrant.Level.EDIT,
        expenses_level=ProfileGrant.Level.EDIT,
        investments_level=ProfileGrant.Level.EDIT,
        movements_level=ProfileGrant.Level.EDIT,
    )
    log_system_event(
        module="bootstrap", action="setup", result="success",
        description="Primeiro administrador criado", workspace=workspace,
        profile=profile, user=user, object_type="User", object_id=str(user.pk),
    )
    return user
