# SPDX-License-Identifier: GPL-3.0-only
from datetime import date
from decimal import Decimal as D

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.finance.models import (
    BankAccount, FinancialProfile, JournalEntry, LedgerLeg, TransactionBatch,
    UnexpectedExpense, Workspace, WorkspaceMembership,
)
from apps.finance.services.ledger import confirm_outflow, reconcile_account


class LedgerServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="example", password="test-password")
        workspace = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=workspace, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=workspace, name="Perfil")
        self.other = FinancialProfile.objects.create(workspace=workspace, name="Outro")
        self.bank = BankAccount.objects.create(
            profile=self.profile, name="Inter", balance=D("100.00"), opening_balance=D("100.00"),
        )
        self.cash = BankAccount.objects.create(
            profile=self.profile, name="Físico", kind="cash", balance=D("40.00"),
            opening_balance=D("40.00"),
        )
        self.expense = UnexpectedExpense.objects.create(
            profile=self.profile, name="Extra", amount=D("100.00"), recorded_on=date(2026, 10, 18),
        )

    def kwargs(self, splits, key):
        return dict(actor=self.user, profile_id=self.profile.pk, kind="unexpected",
                    unexpected_expense_id=self.expense.pk, splits=splits, idempotency_key=key)

    def test_single_outflow_and_idempotency(self):
        kwargs = self.kwargs({self.bank.pk: D("30.00")}, "test-1")
        original = confirm_outflow(**kwargs)
        repeated = confirm_outflow(**kwargs)
        self.assertEqual(original.pk, repeated.pk)
        self.bank.refresh_from_db()
        self.assertEqual(self.bank.balance, D("70.00"))
        self.assertEqual(LedgerLeg.objects.count(), 1)
        self.assertEqual(JournalEntry.objects.count(), 2)
        self.assertEqual(reconcile_account(self.bank), True)

    def test_split_and_insufficient_balance_no_partial_debit(self):
        with self.assertRaises(ValidationError):
            confirm_outflow(**self.kwargs({self.bank.pk: D("90.00"), self.cash.pk: D("50.00")}, "test-2"))
        self.bank.refresh_from_db()
        self.assertEqual(self.bank.balance, D("100.00"))
        self.assertEqual(TransactionBatch.objects.count(), 0)

    def test_cross_profile_blocked(self):
        another = BankAccount.objects.create(
            profile=self.other, name="Caixa", balance=D("90"), opening_balance=D("90"),
        )
        with self.assertRaises(ValidationError):
            confirm_outflow(**self.kwargs({another.pk: D("1")}, "test-3"))
