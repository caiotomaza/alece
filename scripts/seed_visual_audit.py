"""Seed only the isolated ALECE audit database with fictional visual fixtures."""

import os
from pathlib import Path
import sys

if os.environ.get("ALECE_DB_NAME") != "alece_audit" or os.environ.get("ALECE_DB_HOST") not in {
    "127.0.0.1", "localhost", "db",
}:
    raise SystemExit("This seed is restricted to the isolated audit database")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "controller"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import django  # noqa: E402

django.setup()

from decimal import Decimal  # noqa: E402

from django.contrib.auth import get_user_model  # noqa: E402

from apps.finance.models import (  # noqa: E402
    BankAccount, FinancialProfile, InvestmentPosition, RecurringExpense,
    UnexpectedExpense, Workspace,
)
from apps.finance.services.ledger import transfer  # noqa: E402
from apps.finance.services.profiles import create_financial_profile  # noqa: E402
from apps.finance.services.records import save_record  # noqa: E402


def main():
    actor = get_user_model().objects.get(username="auditor_sintetico")
    workspace = Workspace.objects.filter(memberships__user=actor).first()
    if workspace is None:
        raise SystemExit("The isolated audit administrator is missing")
    filled = FinancialProfile.objects.filter(workspace=workspace, name="Visual completo").first()
    if filled is None:
        filled = create_financial_profile(
            workspace_id=workspace.pk, name="Visual completo", emoji="●",
            monthly_income=Decimal("3000.00"), created_by=actor,
        )
    empty = FinancialProfile.objects.filter(workspace=workspace, name="Visual vazio").first()
    if empty is None:
        empty = create_financial_profile(
            workspace_id=workspace.pk, name="Visual vazio", emoji="○",
            monthly_income=None, created_by=actor,
        )
    accounts = []
    for name, balance in (("Banco de teste", "1250.00"), ("Carteira de teste", "400.00")):
        account = BankAccount.objects.filter(profile=filled, name=name).first()
        if account is None:
            account = save_record(actor, filled.pk, BankAccount, {
                "name": name, "kind": "bank" if "Banco" in name else "cash",
                "balance": Decimal(balance),
            })
        accounts.append(account)
    for name, category, amount, day in (
        ("Moradia de teste", "essential", "120.00", 8),
        ("Curso de teste", "strategic", "80.00", 15),
        ("Lazer de teste", "discretionary", "40.00", 22),
    ):
        if not RecurringExpense.objects.filter(profile=filled, name=name).exists():
            save_record(actor, filled.pk, RecurringExpense, {
                "name": name, "category": category, "amount": Decimal(amount),
                "due_day": day,
            })
    for name, category, value, target in (
        ("Proteção de teste", "reserve", "500.00", None),
        ("Patrimônio de teste", "patrimony", "300.00", "1000.00"),
        ("Consumo de teste", "planned", "150.00", "600.00"),
        ("Aprendizado de teste", "development", "50.00", "250.00"),
    ):
        if not InvestmentPosition.objects.filter(profile=filled, name=name).exists():
            save_record(actor, filled.pk, InvestmentPosition, {
                "name": name, "institution": "Instituição fictícia",
                "category": category, "applied_amount": Decimal(value),
                "current_value": Decimal(value),
                "target_amount": Decimal(target) if target else None,
            })
    if not UnexpectedExpense.objects.filter(profile=filled, name="Reparo de teste").exists():
        save_record(actor, filled.pk, UnexpectedExpense, {
            "name": "Reparo de teste", "amount": Decimal("35.00"),
        })
    transfer(
        actor=actor, profile_id=filled.pk, source_id=accounts[0].pk,
        destination_id=accounts[1].pk, amount=Decimal("25.00"),
        idempotency_key="visual-audit-synthetic-transfer-v1",
    )
    print(f"Synthetic audit profiles ready: filled={filled.pk} empty={empty.pk}")


if __name__ == "__main__":
    main()
