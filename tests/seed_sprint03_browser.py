# SPDX-License-Identifier: GPL-3.0-only
"""Synthetic fixture for the isolated browser E2E database only."""
import os
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.test_settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.utils import timezone  # noqa: E402

from apps.finance.models import (  # noqa: E402
    FinancialProfile, Workspace, WorkspaceMembership,
)
from apps.finance.services.profiles import create_financial_profile  # noqa: E402
from apps.finance.services.records import save_record  # noqa: E402
from apps.finance.models import (  # noqa: E402
    BankAccount, InvestmentPosition, RecurringExpense, UnexpectedExpense,
)


def main():
    if (settings.DATABASES["default"]["NAME"] != "alece_e2e_sprint03"
            or not settings.DEBUG or not settings.SECRET_KEY.startswith("sprint03-")):
        raise RuntimeError("Fixture recusada: use apenas o PostgreSQL efêmero E2E do Sprint 03.")
    User = get_user_model()
    admin = User.objects.create_user(
        username="e2e-admin", password="e2e-only-not-production",
    )
    foreign = User.objects.create_user(
        username="e2e-foreign", password="e2e-only-not-production",
    )
    workspace = Workspace.objects.create(name="Núcleo sintético E2E", created_by=admin)
    other = Workspace.objects.create(name="Núcleo isolado E2E", created_by=foreign)
    WorkspaceMembership.objects.create(workspace=workspace, user=admin, role="admin")
    WorkspaceMembership.objects.create(workspace=other, user=foreign, role="admin")
    profile = create_financial_profile(
        workspace_id=workspace.pk, name="Perfil de teste", monthly_income=Decimal("200.00"),
        created_by=admin,
    )
    FinancialProfile.objects.create(workspace=other, name="Perfil privado")
    for name, balance in (("Conta A", Decimal("120.00")), ("Conta B", Decimal("80.00"))):
        save_record(admin, profile.pk, BankAccount, {
            "name": name, "kind": "bank", "balance": balance,
        })
    save_record(admin, profile.pk, RecurringExpense, {
        "name": "Despesa mensal teste", "category": "essential",
        "amount": Decimal("70.00"), "due_day": 31,
    })
    save_record(admin, profile.pk, UnexpectedExpense, {
        "name": "Despesa extra teste", "amount": Decimal("15.00"),
    })
    save_record(admin, profile.pk, InvestmentPosition, {
        "name": "Reserva teste", "category": "reserve",
        "applied_amount": Decimal("0.00"), "current_value": Decimal("0.00"),
        "recorded_on": timezone.localdate(),
    })
    print(f"Synthetic fixture ready: workspace={workspace.pk}, profile={profile.pk}, month={timezone.localdate():%Y-%m}")


if __name__ == "__main__":
    main()
