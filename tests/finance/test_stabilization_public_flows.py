# SPDX-License-Identifier: GPL-3.0-only
"""Regressão de rotas canônicas, seleção de perfis e integridade financeira.

Exige Django e PostgreSQL de testes isolado; não executar na base de produção.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.finance.models import (
    BankAccount, FinancialProfile, InvestmentPosition, TransactionBatch,
    UnexpectedExpense, Workspace, WorkspaceMembership,
)
from apps.finance.profile_selection import SESSION_KEY
from apps.finance.services.ledger import confirm_outflow, reverse_batch


class FinancePublicRedirectAndIntegrityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = get_user_model()
        cls.admin = user.objects.create_user(username="stabilization-admin", password="TestPass12345!")
        cls.common = user.objects.create_user(username="stabilization-common", password="TestPass12345!")
        cls.workspace = Workspace.objects.create(name="Isolado", created_by=cls.admin)
        WorkspaceMembership.objects.create(workspace=cls.workspace, user=cls.admin, role="admin")
        WorkspaceMembership.objects.create(workspace=cls.workspace, user=cls.common, role="common")
        cls.principal = FinancialProfile.objects.create(workspace=cls.workspace, name="Principal")
        cls.secondary = FinancialProfile.objects.create(workspace=cls.workspace, name="Secundário")

    def setUp(self):
        self.client.force_login(self.admin)
        self.bank = BankAccount.objects.create(
            profile=self.principal, name="Banco", balance=Decimal("200"),
            opening_balance=Decimal("200"),
        )
        self.cash = BankAccount.objects.create(
            profile=self.principal, name="Caixa", balance=Decimal("50"),
            opening_balance=Decimal("50"),
        )
        self.expense = UnexpectedExpense.objects.create(
            profile=self.principal, name="Despesa teste", amount=Decimal("30"),
            recorded_on=date(2026, 10, 27),
        )

    def _choose_other(self):
        self.client.get(reverse("visao-geral") + f"?profiles={self.secondary.pk}")
        self.assertEqual(self.client.session[SESSION_KEY]["profile_id"], self.secondary.pk)

    def test_payment_returns_to_public_expenses_and_does_not_change_selected_profile(self):
        self._choose_other()
        url = reverse("finance:payment", args=[self.principal.pk, "unexpected", self.expense.pk])
        response = self.client.post(url, {
            "amount": "30", "accounts": [self.bank.pk], "idempotency_key": "stable-payment",
        })
        self.assertRedirects(response, reverse("despesas") + "?month=2026-10", fetch_redirect_response=False)
        self.assertEqual(self.client.session[SESSION_KEY]["profile_id"], self.secondary.pk)
        self.assertEqual(TransactionBatch.objects.filter(idempotency_key="stable-payment").count(), 1)
        self.bank.refresh_from_db()
        self.assertEqual(self.bank.balance, Decimal("170"))

    def test_transfer_with_all_profiles_keeps_all_and_returns_to_movements(self):
        self.client.get(reverse("visao-geral") + "?profiles=all")
        url = reverse("finance:transfer", args=[self.principal.pk])
        response = self.client.post(url, {
            "source": self.bank.pk, "destination": self.cash.pk,
            "amount": "10", "idempotency_key": "stable-transfer", "note": "Teste",
        })
        self.assertRedirects(response, reverse("movimentacoes"), fetch_redirect_response=False)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertEqual(TransactionBatch.objects.filter(idempotency_key="stable-transfer").count(), 1)

    def test_withdrawal_returns_to_public_investments(self):
        investment = InvestmentPosition.objects.create(
            profile=self.principal, name="Aplicação", category="development",
            applied_amount=Decimal("40"), current_value=Decimal("40"),
        )
        self._choose_other()
        response = self.client.post(reverse("finance:withdrawal", args=[self.principal.pk, investment.pk]), {
            "destination": self.bank.pk, "amount": "10", "idempotency_key": "stable-withdrawal",
        })
        self.assertRedirects(response, reverse("investimentos"), fetch_redirect_response=False)
        self.assertEqual(self.client.session[SESSION_KEY]["profile_id"], self.secondary.pk)

    def test_reversal_redirects_to_public_movements_and_is_idempotent(self):
        original = confirm_outflow(
            actor=self.admin, profile_id=self.principal.pk, kind="unexpected",
            unexpected_expense_id=self.expense.pk, splits={self.bank.pk: Decimal("20")},
            idempotency_key="stable-original",
        )
        self._choose_other()
        route = reverse("finance:reverse-movement", args=[self.principal.pk, original.pk])
        response = self.client.post(route, {"idempotency_key": "stable-reversal"})
        self.assertRedirects(response, reverse("movimentacoes"), fetch_redirect_response=False)
        self.assertEqual(self.client.session[SESSION_KEY]["profile_id"], self.secondary.pk)
        self.assertEqual(TransactionBatch.objects.filter(reversal_of=original).count(), 1)
        self.bank.refresh_from_db()
        self.assertEqual(self.bank.balance, Decimal("200"))
        again = self.client.post(route, {"idempotency_key": "another-reversal"})
        self.assertRedirects(again, reverse("movimentacoes"), fetch_redirect_response=False)
        self.assertEqual(TransactionBatch.objects.filter(reversal_of=original).count(), 1)

    def test_profile_forms_cancel_to_current_public_management_pages(self):
        response = self.client.get(reverse("finance:profile-edit", args=[self.principal.pk]))
        self.assertEqual(response.context["cancel_url"], reverse("configuracoes-perfis"))
        response = self.client.get(reverse("finance:income-edit", args=[self.principal.pk]))
        self.assertEqual(response.context["cancel_url"], reverse("visao-geral"))

    def test_user_without_grant_cannot_post_to_foreign_profile_and_no_batch_is_created(self):
        self.client.force_login(self.common)
        response = self.client.post(reverse("finance:transfer", args=[self.principal.pk]), {
            "source": self.bank.pk, "destination": self.cash.pk,
            "amount": "10", "idempotency_key": "attempt-denied",
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(TransactionBatch.objects.exists())

    def test_idempotent_replay_never_debits_twice(self):
        kwargs = {
            "actor": self.admin, "profile_id": self.principal.pk,
            "kind": "unexpected", "unexpected_expense_id": self.expense.pk,
            "splits": {self.bank.pk: Decimal("20")}, "idempotency_key": "stable-replay",
        }
        one = confirm_outflow(**kwargs)
        two = confirm_outflow(**kwargs)
        self.assertEqual(one.pk, two.pk)
        self.bank.refresh_from_db()
        self.assertEqual(self.bank.balance, Decimal("180"))
        with self.assertRaises(ValidationError):
            confirm_outflow(**{**kwargs, "splits": {self.bank.pk: Decimal("25")}})
        self.assertEqual(TransactionBatch.objects.count(), 1)
