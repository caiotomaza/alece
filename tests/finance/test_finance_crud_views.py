# SPDX-License-Identifier: GPL-3.0-only
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.finance.models import (
    BankAccount, FinancialProfile, InvestmentPosition, LedgerLeg, RecurringExpense,
    TransactionBatch, UnexpectedExpense, Workspace, WorkspaceMembership,
)


class AuthenticatedFinanceBrowserFlowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username="web-admin", password="web-test-only")
        self.stranger = User.objects.create_user(username="web-stranger", password="web-test-only")
        self.workspace = Workspace.objects.create(name="Sintético", created_by=self.admin)
        self.foreign_workspace = Workspace.objects.create(name="Externo", created_by=self.stranger)
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.admin, role="admin")
        WorkspaceMembership.objects.create(
            workspace=self.foreign_workspace, user=self.stranger, role="admin",
        )
        self.profile = FinancialProfile.objects.create(workspace=self.workspace, name="Principal")
        self.foreign_profile = FinancialProfile.objects.create(
            workspace=self.foreign_workspace, name="Segredo",
        )
        self.client.post(reverse("login"), {"username": "web-admin", "password": "web-test-only"})

    def test_full_monthly_browser_flow_partial_split_and_reversal(self):
        create_account = reverse("finance:account-create", args=[self.profile.pk])
        self.assertEqual(self.client.post(create_account, {
            "name": "Banco A", "kind": "bank", "balance": "50.00",
        }).status_code, 302)
        self.assertEqual(self.client.post(create_account, {
            "name": "Banco B", "kind": "bank", "balance": "40.00",
        }).status_code, 302)
        accounts = list(BankAccount.objects.filter(profile=self.profile).order_by("pk"))
        self.assertEqual(self.client.post(reverse("finance:recurring-create", args=[self.profile.pk]), {
            "name": "Mensalidade", "category": "essential", "amount": "70.00", "due_day": "31",
        }).status_code, 302)
        expense = RecurringExpense.objects.get(profile=self.profile)
        overview = reverse("finance:overview", args=[self.workspace.pk])
        response = self.client.get(overview, {"month": "2026-10"})
        self.assertContains(response, "Este mês")
        self.assertContains(response, "Mensalidade")
        pay = reverse("finance:payment", args=[self.profile.pk, "recurring", expense.pk])
        form = self.client.get(pay, {"month": "2026-10"})
        self.assertContains(form, 'data-balance="50.00"')
        self.assertContains(form, "Ainda falta")
        first = self.client.post(pay, {
            "month": "2026-10", "amount": "20.00", "accounts": [accounts[0].pk],
            "idempotency_key": "browser-partial",
        })
        self.assertEqual(first.status_code, 302)
        second = self.client.post(pay, {
            "month": "2026-10", "amount": "50.00",
            "accounts": [account.pk for account in accounts],
            "idempotency_key": "browser-rest",
        })
        self.assertEqual(second.status_code, 302)
        for account, expected in zip(accounts, (Decimal("0"), Decimal("20"))):
            account.refresh_from_db()
            self.assertEqual(account.balance, expected)
        self.assertEqual(LedgerLeg.objects.filter(batch__kind="recurring").count(), 3)
        self.assertContains(self.client.get(overview, {"month": "2026-10"}), "Desmarcar e estornar")
        uncheck = reverse("finance:reverse-item", args=[self.profile.pk, "recurring", expense.pk])
        self.assertEqual(self.client.post(uncheck, {
            "month": "2026-10", "idempotency_key": "browser-uncheck",
        }).status_code, 302)
        for account, expected in zip(accounts, (Decimal("50"), Decimal("40"))):
            account.refresh_from_db()
            self.assertEqual(account.balance, expected)
        self.assertEqual(TransactionBatch.objects.filter(kind="reversal").count(), 2)

    def test_cross_profile_account_and_csrf_rejected(self):
        own = BankAccount.objects.create(
            profile=self.profile, name="Própria", balance=Decimal("50"),
            opening_balance=Decimal("50"),
        )
        foreign = BankAccount.objects.create(
            profile=self.foreign_profile, name="Alheia", balance=Decimal("100"),
            opening_balance=Decimal("100"),
        )
        expense = UnexpectedExpense.objects.create(
            profile=self.profile, name="Extra", amount=Decimal("10"),
            recorded_on=date(2026, 10, 18),
        )
        pay = reverse("finance:payment", args=[self.profile.pk, "unexpected", expense.pk])
        self.assertEqual(self.client.post(pay, {
            "amount": "10", "accounts": [foreign.pk], "idempotency_key": "foreign-attempt",
        }).status_code, 200)
        self.assertFalse(TransactionBatch.objects.exists())
        self.assertEqual(self.client.get(reverse(
            "finance:payment", args=[self.foreign_profile.pk, "unexpected", expense.pk],
        )).status_code, 403)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.admin)
        self.assertEqual(csrf_client.post(pay, {
            "amount": "10", "accounts": [own.pk], "idempotency_key": "csrf-attempt",
        }).status_code, 403)
        self.assertFalse(TransactionBatch.objects.exists())

    def test_transfer_application_and_withdrawal_routes(self):
        a = BankAccount.objects.create(
            profile=self.profile, name="A", balance=Decimal("100"), opening_balance=Decimal("100"),
        )
        b = BankAccount.objects.create(
            profile=self.profile, name="B", balance=Decimal("20"), opening_balance=Decimal("20"),
        )
        position = InvestmentPosition.objects.create(
            profile=self.profile, name="Reserva", category="reserve",
        )
        self.assertEqual(self.client.post(reverse("finance:transfer", args=[self.profile.pk]), {
            "source": a.pk, "destination": b.pk, "amount": "10",
            "idempotency_key": "web-transfer",
        }).status_code, 302)
        self.assertEqual(self.client.post(reverse(
            "finance:payment", args=[self.profile.pk, "application", position.pk],
        ), {"amount": "30", "accounts": [a.pk], "idempotency_key": "web-application"}).status_code, 302)
        self.assertEqual(self.client.post(reverse(
            "finance:withdrawal", args=[self.profile.pk, position.pk],
        ), {"amount": "5", "destination": b.pk,
            "idempotency_key": "web-withdrawal"}).status_code, 302)
        a.refresh_from_db()
        b.refresh_from_db()
        position.refresh_from_db()
        self.assertEqual((a.balance, b.balance, position.current_value),
                         (Decimal("60"), Decimal("35"), Decimal("25")))
        movements = self.client.get(reverse("finance:movements", args=[self.workspace.pk]))
        self.assertContains(movements, "Transferência")
        self.assertContains(movements, "Aplicação")
        self.assertContains(movements, "Resgate")

    def test_unknown_balance_distinguished_from_zero(self):
        unknown_acc = BankAccount.objects.create(
            profile=self.profile, name="Conta Saldo Oculto", balance=None, opening_balance=None,
        )
        overview = reverse("finance:overview", args=[self.workspace.pk])
        resp = self.client.get(overview, {"month": "2026-10"})
        self.assertContains(resp, "Saldos conhecidos")
        self.assertContains(resp, "<strong>Desconhecido</strong>")
        self.assertContains(resp, "Saldo atual conhecido: Desconhecido")
        self.assertContains(resp, "Projetado: —")

        # Now update to known zero
        unknown_acc.balance = Decimal("0.00")
        unknown_acc.opening_balance = Decimal("0.00")
        unknown_acc.save()

        resp_zero = self.client.get(overview, {"month": "2026-10"})
        self.assertContains(resp_zero, "<strong>R$ 0,00</strong>")
        self.assertContains(resp_zero, "Saldo atual conhecido: R$ 0,00")

    def test_movement_detail_modal_and_reversal_integration(self):
        a = BankAccount.objects.create(
            profile=self.profile, name="Conta Origem", balance=Decimal("100.00"), opening_balance=Decimal("100.00"),
        )
        b = BankAccount.objects.create(
            profile=self.profile, name="Conta Destino", balance=Decimal("50.00"), opening_balance=Decimal("50.00"),
        )
        transfer_resp = self.client.post(reverse("finance:transfer", args=[self.profile.pk]), {
            "source": a.pk, "destination": b.pk, "amount": "30.00",
            "note": "Nota inicial", "idempotency_key": "modal-transfer-test",
        })
        self.assertEqual(transfer_resp.status_code, 302)
        batch = TransactionBatch.objects.get(idempotency_key="modal-transfer-test")

        detail_url = reverse("finance:movement-detail", args=[self.profile.pk, batch.pk])
        resp = self.client.get(detail_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Editar movimentação")
        self.assertContains(resp, "Revise o registro antes de confirmar.")
        self.assertContains(resp, "Transferência")
        self.assertContains(resp, "R$ 30,00")
        self.assertContains(resp, "Estornar")
        self.assertContains(resp, "data-confirm-reversal")
        self.assertContains(resp, "Cancelar")

        # Execute reversal from the modal
        rev_url = reverse("finance:reverse-movement", args=[self.profile.pk, batch.pk])
        rev_resp = self.client.post(rev_url, {"idempotency_key": "modal-reversal-key"})
        self.assertEqual(rev_resp.status_code, 302)
        a.refresh_from_db()
        b.refresh_from_db()
        self.assertEqual(a.balance, Decimal("100.00"))
        self.assertEqual(b.balance, Decimal("50.00"))

        # View reversed movement detail
        rev_detail = self.client.get(detail_url)
        self.assertContains(rev_detail, "Estornado")
        self.assertNotContains(rev_detail, 'id="movement-edit-reverse"')

