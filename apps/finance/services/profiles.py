# SPDX-License-Identifier: GPL-3.0-only
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.finance.models import FinancialProfile, ProfileGrant, Workspace


@transaction.atomic
def create_financial_profile(
    *, workspace_id: int, name: str, emoji: str = "", monthly_income=None, created_by=None,
):
    if created_by is not None:
        from apps.core.permissions import require_workspace_admin
        require_workspace_admin(created_by, workspace_id)
    # Lock the parent to avoid concurrent requests exceeding five profiles.
    workspace = Workspace.objects.select_for_update().get(pk=workspace_id)
    if FinancialProfile.objects.filter(workspace=workspace, is_archived=False).count() >= 5:
        raise ValidationError("Máximo de cinco perfis financeiros por núcleo.")
    profile = FinancialProfile(
        workspace=workspace, name=name.strip(), emoji=emoji, monthly_income=monthly_income,
    )
    profile.full_clean()
    profile.save()
    if created_by is not None:
        ProfileGrant.objects.create(
            membership=workspace.memberships.get(user=created_by),
            profile=profile, can_view=True, can_edit=True,
        )
    return profile


@transaction.atomic
def update_financial_profile(user, profile_id, data):
    from apps.core.permissions import require_profile_view, require_workspace_admin
    profile = require_profile_view(user, profile_id)
    require_workspace_admin(user, profile.workspace_id)
    Workspace.objects.select_for_update().get(pk=profile.workspace_id)
    profile = FinancialProfile.objects.select_for_update().get(pk=profile_id)
    if profile.is_archived and not data.get("is_archived", True):
        if FinancialProfile.objects.filter(workspace_id=profile.workspace_id, is_archived=False).count() >= 5:
            raise ValidationError("Máximo de cinco perfis ativos por núcleo.")
    allowed = {"name", "emoji", "monthly_income", "is_archived"}
    if set(data) - allowed:
        raise ValidationError("Campo de perfil não permitido.")
    for key, value in data.items():
        setattr(profile, key, value.strip() if isinstance(value, str) else value)
    profile.full_clean()
    profile.save()
    return profile
