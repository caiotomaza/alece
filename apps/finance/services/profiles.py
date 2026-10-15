# SPDX-License-Identifier: GPL-3.0-only
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.finance.models import FinancialProfile, Workspace


@transaction.atomic
def create_financial_profile(*, workspace_id: int, name: str, emoji: str = ""):
    # Lock the parent to avoid concurrent requests exceeding five profiles.
    workspace = Workspace.objects.select_for_update().get(pk=workspace_id)
    if FinancialProfile.objects.filter(workspace=workspace).count() >= 5:
        raise ValidationError("Máximo de cinco perfis financeiros por núcleo.")
    return FinancialProfile.objects.create(workspace=workspace, name=name.strip(), emoji=emoji)
