# SPDX-License-Identifier: GPL-3.0-only
import io
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TransactionTestCase

from apps.finance.models import BankAccount, FinancialProfile, Workspace


class FinancePreflightTests(TransactionTestCase):
    def test_read_only_report_and_strict_reconciliation_gate(self):
        user = get_user_model().objects.create_user(username="preflight")
        workspace = Workspace.objects.create(name="Synthetic", created_by=user)
        profile = FinancialProfile.objects.create(workspace=workspace, name="Synthetic")
        account = BankAccount.objects.create(
            profile=profile, name="Legacy", balance=Decimal("3.00"),
        )
        output = io.StringIO()
        call_command("preflight_finance", stdout=output)
        report = json.loads(output.getvalue())
        self.assertEqual(report["reserve_manual_target_positions"], 0)
        self.assertEqual(report["accounts_without_reconciled_opening"], 1)
        self.assertEqual(report["modified_rows"], 0)
        with self.assertRaises(CommandError):
            call_command("preflight_finance", strict=True, stdout=io.StringIO())
        account.refresh_from_db()
        self.assertIsNone(account.opening_balance)
        self.assertEqual(account.balance, Decimal("3.00"))
