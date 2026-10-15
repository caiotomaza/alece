# SPDX-License-Identifier: GPL-3.0-only
from decimal import Decimal as D

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.finance.models import BankAccount, FinancialProfile, LedgerLeg, TransactionBatch, Workspace
from apps.finance.services.ledger import confirm_outflow


class LedgerServiceTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="example", password="test-password")
        workspace = Workspace.objects.create(name="Teste", created_by=user)
        self.profile = FinancialProfile.objects.create(workspace=workspace, name="Perfil")
        self.other = FinancialProfile.objects.create(workspace=workspace, name="Outro")
        self.bank = BankAccount.objects.create(profile=self.profile, name="Inter", balance=D("100.00"))
        self.cash = BankAccount.objects.create(profile=self.profile, name="Físico", kind="cash", balance=D("40.00"))

    def test_single_outflow_and_idempotency(self):
        kwargs = dict(profile_id=self.profile.pk, kind="unexpected", splits={self.bank.pk: D("30.00")}, idempotency_key="test-1")
        original = confirm_outflow(**kwargs)
        repeated = confirm_outflow(**kwargs)
        self.assertEqual(original.pk, repeated.pk)
        self.bank.refresh_from_db()
        self.assertEqual(self.bank.balance, D("70.00"))
        self.assertEqual(LedgerLeg.objects.count(), 1)

    def test_split_and_insufficient_balance_no_partial_debit(self):
        with self.assertRaises(ValidationError):
            confirm_outflow(profile_id=self.profile.pk, kind="unexpected", splits={self.bank.pk: D("90.00"), self.cash.pk: D("50.00")}, idempotency_key="test-2")
        self.bank.refresh_from_db()
        self.assertEqual(self.bank.balance, D("100.00"))
        self.assertEqual(TransactionBatch.objects.count(), 0)

    def test_cross_profile_blocked(self):
        another = BankAccount.objects.create(profile=self.other, name="Caixa", balance=D("90"))
        with self.assertRaises(ValidationError):
            confirm_outflow(profile_id=self.profile.pk, kind="unexpected", splits={another.pk: D("1")}, idempotency_key="test-3")
