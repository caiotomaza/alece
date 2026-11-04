# SPDX-License-Identifier: GPL-3.0-only
from django.db import transaction

from apps.finance.models import BankAccount, FinancialProfile


@transaction.atomic
def create_bank_account(*, profile_id: int, name: str, kind: str, balance=None, created_by=None):
    if created_by is not None:
        from apps.core.permissions import require_module
        require_module(created_by, profile_id, "accounts", "edit")
    # Serialize creation within a profile, including duplicate-name validation.
    profile = FinancialProfile.objects.select_for_update().get(pk=profile_id)
    account = BankAccount(
        profile=profile, name=name.strip(), kind=kind,
        balance=balance, opening_balance=balance,
    )
    account.full_clean()
    account.save()
    return account
