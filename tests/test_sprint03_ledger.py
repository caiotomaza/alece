# SPDX-License-Identifier: GPL-3.0-only
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal as D
from threading import Barrier

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DatabaseError, close_old_connections, connection, connections, transaction
from django.db.models import Sum
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.finance.models import (
    BankAccount, FinancialProfile, InvestmentPosition, JournalEntry, LedgerLeg,
    MonthlyExpense, RecurringExpense, TransactionBatch, UnexpectedExpense, Workspace,
    WorkspaceMembership,
)
from apps.finance.services.ledger import (
    confirm_outflow, reconcile_account, reverse_batch, reverse_item_payments,
    transfer, withdraw_investment,
)
from apps.finance.services.monthly import monthly_items
from apps.finance.services.metrics import profile_summary


class LedgerWorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username="ledger-admin")
        self.common = User.objects.create_user(username="ledger-common")
        self.foreign = User.objects.create_user(username="ledger-foreign")
        self.ws = Workspace.objects.create(name="Fictício", created_by=self.admin)
        self.other_ws = Workspace.objects.create(name="Isolado", created_by=self.foreign)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.admin, role="admin")
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.common, role="common")
        WorkspaceMembership.objects.create(workspace=self.other_ws, user=self.foreign, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.other_profile = FinancialProfile.objects.create(workspace=self.other_ws, name="Outro")
        self.bank = BankAccount.objects.create(
            profile=self.profile, name="Banco A", balance=D("100.00"), opening_balance=D("100.00"),
        )
        self.cash = BankAccount.objects.create(
            profile=self.profile, name="Banco B", balance=D("50.00"), opening_balance=D("50.00"),
        )
        self.month = date(2026, 10, 1)
        self.recurring = RecurringExpense.objects.create(
            profile=self.profile, name="Serviço", category="essential", amount=D("90.00"), due_day=31,
        )
        self.unexpected = UnexpectedExpense.objects.create(
            profile=self.profile, name="Reparo", amount=D("40.00"), recorded_on=date(2026, 10, 18),
        )

    def pay(self, *, kind="recurring", splits=None, key="pay-1", **links):
        default_link = ({"recurring_expense_id": self.recurring.pk, "competence_month": self.month}
                        if kind == "recurring" else
                        {"unexpected_expense_id": self.unexpected.pk} if kind == "unexpected" else {})
        default_link.update(links)
        return confirm_outflow(
            actor=self.admin, profile_id=self.profile.pk, kind=kind,
            splits=splits or {self.bank.pk: D("20.00")}, idempotency_key=key,
            **default_link,
        )

    def assert_balanced(self, batch):
        amounts = batch.journal_entries.aggregate(debit=Sum("debit"), credit=Sum("credit"))
        self.assertEqual(amounts["debit"], amounts["credit"])
        self.assertEqual(amounts["debit"], batch.amount)

    def test_partial_monthly_payment_split_idempotency_and_frozen_competence(self):
        batch = self.pay(splits={self.bank.pk: D("30.00"), self.cash.pk: D("20.00")})
        self.assertEqual(self.pay(splits={self.bank.pk: D("30.00"), self.cash.pk: D("20.00")}).pk, batch.pk)
        self.assertEqual(LedgerLeg.objects.filter(batch=batch).count(), 2)
        self.assert_balanced(batch)
        self.assertEqual(batch.created_by, self.admin)
        self.assertEqual(MonthlyExpense.objects.get(recurring_expense=self.recurring).amount, D("90"))
        self.recurring.amount = D("120")
        self.recurring.save(update_fields=["amount"])
        item = monthly_items(self.profile, self.month)[0]
        self.assertEqual((item["due"], item["paid"], item["remaining"]),
                         (D("90"), D("50"), D("40")))
        with self.assertRaises(ValidationError):
            self.pay(splits={self.bank.pk: D("41")}, key="pay-too-much")
        self.pay(splits={self.bank.pk: D("40")}, key="pay-rest")
        self.bank.refresh_from_db()
        self.cash.refresh_from_db()
        self.assertEqual(self.bank.balance, D("30"))
        self.assertEqual(self.cash.balance, D("30"))
        self.assertTrue(reconcile_account(self.bank))
        self.assertTrue(reconcile_account(self.cash))
        self.assertEqual(monthly_items(self.profile, self.month)[0]["remaining"], D("0"))

    def test_reverse_all_partials_restores_balances_and_keeps_history(self):
        first = self.pay(kind="unexpected", splits={self.bank.pk: D("15")}, key="u1")
        second = self.pay(kind="unexpected", splits={self.cash.pk: D("25")}, key="u2")
        reversals = reverse_item_payments(
            actor=self.admin, profile_id=self.profile.pk, kind="unexpected",
            object_id=self.unexpected.pk, competence_month=self.month, idempotency_key="reverse-u",
        )
        self.assertEqual(len(reversals), 2)
        self.assertEqual({row.reversal_of_id for row in reversals}, {first.pk, second.pk})
        self.bank.refresh_from_db()
        self.cash.refresh_from_db()
        self.assertEqual((self.bank.balance, self.cash.balance), (D("100"), D("50")))
        self.assertEqual(TransactionBatch.objects.count(), 4)
        self.assert_balanced(reversals[0])
        self.assertEqual(monthly_items(self.profile, self.month)[1]["paid"], D("0"))
        with self.assertRaises(ValidationError):
            reverse_batch(actor=self.admin, profile_id=self.profile.pk, batch_id=first.pk,
                          idempotency_key="different-key")

    def test_transfer_and_reversal_do_not_become_income_or_expense(self):
        batch = transfer(
            actor=self.admin, profile_id=self.profile.pk, source_id=self.bank.pk,
            destination_id=self.cash.pk, amount=D("40"), idempotency_key="transfer-1",
        )
        self.assert_balanced(batch)
        self.assertIsNone(batch.recurring_expense_id)
        self.assertIsNone(batch.unexpected_expense_id)
        self.bank.refresh_from_db()
        self.cash.refresh_from_db()
        self.assertEqual((self.bank.balance, self.cash.balance), (D("60"), D("90")))
        reversal = reverse_batch(
            actor=self.admin, profile_id=self.profile.pk, batch_id=batch.pk,
            idempotency_key="transfer-reverse",
        )
        self.assert_balanced(reversal)
        self.bank.refresh_from_db()
        self.cash.refresh_from_db()
        self.assertEqual((self.bank.balance, self.cash.balance), (D("100"), D("50")))

    def test_application_withdrawal_cost_basis_and_reversal(self):
        position = InvestmentPosition.objects.create(
            profile=self.profile, name="Reserva", category="reserve",
            applied_amount=D("20"), current_value=D("25"),
        )
        application = self.pay(
            kind="application", splits={self.bank.pk: D("10")}, key="apply",
            investment_id=position.pk,
        )
        self.assert_balanced(application)
        position.refresh_from_db()
        self.assertEqual((position.applied_amount, position.current_value), (D("30"), D("35")))
        withdrawal = withdraw_investment(
            actor=self.admin, profile_id=self.profile.pk, investment_id=position.pk,
            destination_id=self.cash.pk, amount=D("7"), idempotency_key="withdraw",
        )
        self.assert_balanced(withdrawal)
        self.assertEqual(withdrawal.investment_applied_delta, D("-6"))
        position.refresh_from_db()
        self.assertEqual((position.applied_amount, position.current_value), (D("24"), D("28")))
        reverse_batch(actor=self.admin, profile_id=self.profile.pk, batch_id=withdrawal.pk,
                      idempotency_key="reverse-withdraw")
        position.refresh_from_db()
        self.assertEqual((position.applied_amount, position.current_value), (D("30"), D("35")))

    def test_monthly_application_plan_stays_frozen_and_does_not_resuggest_paid_cash(self):
        month = timezone.localdate().replace(day=1)
        self.profile.monthly_income = D("100")
        self.profile.save(update_fields=["monthly_income"])
        self.recurring.amount = D("10")
        self.recurring.save(update_fields=["amount"])
        position = InvestmentPosition.objects.create(
            profile=self.profile, name="Reserva", category="reserve",
        )
        before = profile_summary(self.profile, month)
        self.assertEqual(before["allocation"]["reserve"], D("90"))
        self.pay(kind="application", investment_id=position.pk,
                 competence_month=month, splits={self.bank.pk: D("30")}, key="plan-1")
        after = profile_summary(self.profile, month)
        self.assertEqual(after["applications_confirmed"], D("30"))
        self.assertEqual(after["allocation"]["reserve"], D("60"))
        planned = [row for row in monthly_items(
            self.profile, month, include_applications=True, summary=after,
        ) if row["kind"] == "application"]
        self.assertEqual((planned[0]["due"], planned[0]["paid"], planned[0]["remaining"]),
                         (D("90"), D("30"), D("60")))
        self.pay(kind="application", investment_id=position.pk,
                 competence_month=month, splits={self.bank.pk: D("60")}, key="plan-2")
        position.refresh_from_db()
        self.assertEqual(position.current_value, D("90"))
        with self.assertRaises(ValidationError):
            self.pay(kind="application", investment_id=position.pk,
                     competence_month=month, splits={self.cash.pk: D("1")}, key="plan-over")
        reverse_item_payments(
            actor=self.admin, profile_id=self.profile.pk, kind="application",
            object_id=position.pk, competence_month=month, idempotency_key="reverse-plan",
        )
        position.refresh_from_db()
        self.bank.refresh_from_db()
        self.assertEqual((position.current_value, self.bank.balance), (D("0"), D("100")))

    def test_unknown_or_unreconciled_account_cannot_move(self):
        self.bank.opening_balance = None
        self.bank.save(update_fields=["opening_balance"])
        with self.assertRaises(ValidationError):
            self.pay()
        self.assertIsNone(reconcile_account(self.bank))
        self.bank.balance = None
        self.bank.save(update_fields=["balance"])
        with self.assertRaises(ValidationError):
            self.pay()

    def test_no_common_access_and_cross_profile_isolation(self):
        with self.assertRaises(PermissionDenied):
            confirm_outflow(actor=self.common, profile_id=self.profile.pk, kind="unexpected",
                            splits={self.bank.pk: D("1")}, unexpected_expense_id=self.unexpected.pk,
                            idempotency_key="common-denied")
        foreign_account = BankAccount.objects.create(
            profile=self.other_profile, name="Fora", balance=D("50"), opening_balance=D("50"),
        )
        with self.assertRaises(ValidationError):
            self.pay(splits={foreign_account.pk: D("1")}, key="cross-account")
        with self.assertRaises(PermissionDenied):
            reverse_batch(actor=self.foreign, profile_id=self.profile.pk, batch_id=999,
                          idempotency_key="cross-reverse")


class LedgerPostgresConcurrencyTests(TransactionTestCase):
    def test_concurrent_partial_payments_do_not_overpay(self):
        if connection.vendor != "postgresql":
            self.skipTest("Exige PostgreSQL")
        user = get_user_model().objects.create_user(username="concurrent-ledger")
        workspace = Workspace.objects.create(name="Isolado", created_by=user)
        WorkspaceMembership.objects.create(workspace=workspace, user=user, role="admin")
        profile = FinancialProfile.objects.create(workspace=workspace, name="Teste")
        account = BankAccount.objects.create(
            profile=profile, name="Banco", balance=D("100"), opening_balance=D("100"),
        )
        expense = RecurringExpense.objects.create(
            profile=profile, name="Plano", category="essential", amount=D("100"), due_day=1,
        )
        barrier = Barrier(2)

        def pay(index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                confirm_outflow(
                    actor=user, profile_id=profile.pk, kind="recurring",
                    splits={account.pk: D("60")}, recurring_expense_id=expense.pk,
                    competence_month=date(2026, 10, 1), idempotency_key=f"concurrent-{index}",
                )
                return "paid"
            except ValidationError:
                return "limited"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(pay, [1, 2]))
        self.assertCountEqual(results, ["paid", "limited"])
        account.refresh_from_db()
        self.assertEqual(account.balance, D("40"))
        self.assertEqual(TransactionBatch.objects.filter(profile=profile).count(), 1)

    def test_database_rejects_unbalanced_and_mutated_posted_history(self):
        if connection.vendor != "postgresql":
            self.skipTest("Exige PostgreSQL")
        user = get_user_model().objects.create_user(username="journal-integrity")
        workspace = Workspace.objects.create(name="Isolado", created_by=user)
        WorkspaceMembership.objects.create(workspace=workspace, user=user, role="admin")
        profile = FinancialProfile.objects.create(workspace=workspace, name="Teste")
        with self.assertRaises(DatabaseError), transaction.atomic():
            TransactionBatch.objects.create(
                profile=profile, created_by=user, kind="transfer", amount=D("1"),
                occurred_on=date(2026, 10, 18),
            )
        account = BankAccount.objects.create(
            profile=profile, name="Banco", balance=D("20"), opening_balance=D("20"),
        )
        expense = UnexpectedExpense.objects.create(
            profile=profile, name="Extra", amount=D("5"), recorded_on=date(2026, 10, 18),
        )
        batch = confirm_outflow(
            actor=user, profile_id=profile.pk, kind="unexpected", splits={account.pk: D("5")},
            unexpected_expense_id=expense.pk, idempotency_key="immutable",
        )
        with self.assertRaises(DatabaseError), transaction.atomic():
            JournalEntry.objects.filter(batch=batch).update(debit=D("2"))
        with self.assertRaises(DatabaseError), transaction.atomic():
            TransactionBatch.objects.filter(pk=batch.pk).delete()
