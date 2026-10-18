# SPDX-License-Identifier: GPL-3.0-only
"""Workspace administrator grants module rights to one common member/profile."""
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.core.permissions import require_workspace_admin
from apps.finance.models import FinancialProfile, ProfileGrant, WorkspaceMembership

GRANT_FIELDS = (
    "overview_level", "accounts_level", "expenses_level",
    "investments_level", "movements_level",
)


@transaction.atomic
def save_grant(*, actor, profile_id, membership_id, levels):
    profile = FinancialProfile.objects.select_for_update().get(pk=profile_id)
    require_workspace_admin(actor, profile.workspace_id)
    member = WorkspaceMembership.objects.select_for_update().filter(
        pk=membership_id, workspace_id=profile.workspace_id, role=WorkspaceMembership.Role.COMMON,
    ).first()
    if member is None:
        raise ValidationError("Membro comum deste núcleo não encontrado.")
    if set(levels) != set(GRANT_FIELDS):
        raise ValidationError("Informe todos os módulos explicitamente.")
    if any(value not in ProfileGrant.Level.values for value in levels.values()):
        raise ValidationError("Nível de permissão inválido.")
    grant, _ = ProfileGrant.objects.select_for_update().get_or_create(
        membership=member, profile=profile,
    )
    for field, value in levels.items():
        setattr(grant, field, value)
    grant.can_view = any(value != ProfileGrant.Level.NONE for value in levels.values())
    grant.can_edit = any(value == ProfileGrant.Level.EDIT for value in levels.values())
    grant.full_clean()
    grant.save()
    return grant
