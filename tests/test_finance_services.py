# SPDX-License-Identifier: GPL-3.0-only
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.finance.models import (
    BankAccount, FinancialProfile, InvestmentPosition, LedgerLeg, ProfileGrant,
    RecurringExpense, ReservePolicy, TransactionBatch, UnexpectedExpense, Workspace,
    WorkspaceMembership,
)
from apps.finance.services.profiles import create_financial_profile, update_financial_profile
from apps.finance.services.records import delete_record, save_record, update_income


class RegistrationServicesTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username="registration-admin")
        self.common = get_user_model().objects.create_user(username="registration-common")
        self.workspace = Workspace.objects.create(name="Núcleo", created_by=self.admin)
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.admin, role="admin")
        self.membership = WorkspaceMembership.objects.create(workspace=self.workspace, user=self.common)
        self.profile = create_financial_profile(workspace_id=self.workspace.pk, name="Principal")
        self.grant = ProfileGrant.objects.create(membership=self.membership, profile=self.profile, can_edit=True)

    def test_active_limit_counts_only_active_and_reactivation_checks_capacity(self):
        update_financial_profile(self.admin, self.profile.pk, {"is_archived": True})
        for index in range(5):
            create_financial_profile(workspace_id=self.workspace.pk, name=f"Ativo {index}")
        with self.assertRaises(ValidationError):
            update_financial_profile(self.admin, self.profile.pk, {"is_archived": False})
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.is_archived)
        with self.assertRaises(ValidationError):
            create_financial_profile(workspace_id=self.workspace.pk, name="Excedente")

    def test_common_income_edit_does_not_allow_profile_administration(self):
        update_income(self.common, self.profile.pk, Decimal("0.00"))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.monthly_income, Decimal("0.00"))
        update_income(self.common, self.profile.pk, None)
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.monthly_income)
        with self.assertRaises(PermissionDenied):
            update_financial_profile(self.common, self.profile.pk, {"name": "Outro"})

    def test_archive_blocks_financial_writes(self):
        update_financial_profile(self.admin, self.profile.pk, {"is_archived": True})
        with self.assertRaises(ValidationError):
            update_income(self.admin, self.profile.pk, Decimal("1"))
        with self.assertRaises(ValidationError):
            save_record(self.admin, self.profile.pk, BankAccount, {"name": "Nova", "kind": "bank"})

    def test_revocation_applies_to_next_service_call(self):
        self.grant.delete()
        with self.assertRaises(PermissionDenied):
            save_record(self.common, self.profile.pk, BankAccount, {"name": "Nova", "kind": "bank"})

    def test_rejects_profile_reassignment_and_foreign_objects(self):
        account = BankAccount.objects.create(profile=self.profile, name="Original")
        other = create_financial_profile(workspace_id=self.workspace.pk, name="Outro")
        with self.assertRaises(ValidationError):
            save_record(self.admin, self.profile.pk, BankAccount, {"profile_id": other.pk}, account.pk)
        with self.assertRaises(BankAccount.DoesNotExist):
            save_record(self.admin, other.pk, BankAccount, {"name": "Invasão"}, account.pk)
        with self.assertRaises(BankAccount.DoesNotExist):
            delete_record(self.admin, other.pk, BankAccount, account.pk)

    def test_unexpected_uses_server_date_and_does_not_debit(self):
        account = BankAccount.objects.create(profile=self.profile, name="Banco", balance=Decimal("50"))
        with patch("apps.finance.services.records.timezone.localdate", return_value=date(2026, 10, 18)):
            expense = save_record(self.common, self.profile.pk, UnexpectedExpense, {"name": "Extra", "amount": Decimal("20")})
        self.assertEqual(expense.recorded_on, date(2026, 10, 18))
        account.refresh_from_db()
        self.assertEqual(account.balance, Decimal("50"))
        self.assertFalse(TransactionBatch.objects.exists())
        with self.assertRaises(ValidationError):
            save_record(self.common, self.profile.pk, UnexpectedExpense, {"recorded_on": date(2000, 1, 1)}, expense.pk)

    def test_linked_account_keeps_balance_and_history_but_can_archive(self):
        account = BankAccount.objects.create(profile=self.profile, name="Banco", balance=Decimal("50"))
        batch = TransactionBatch.objects.create(profile=self.profile, kind="unexpected", amount=Decimal("10"), occurred_on=date(2026, 10, 18))
        LedgerLeg.objects.create(batch=batch, account=account, delta=Decimal("-10"))
        with self.assertRaises(ValidationError):
            save_record(self.admin, self.profile.pk, BankAccount, {"balance": Decimal("100")}, account.pk)
        with self.assertRaises(ValidationError):
            delete_record(self.admin, self.profile.pk, BankAccount, account.pk)
        save_record(self.admin, self.profile.pk, BankAccount, {"is_archived": True}, account.pk)
        account.refresh_from_db()
        self.assertTrue(account.is_archived)
        self.assertEqual(account.balance, Decimal("50"))
        self.assertEqual(LedgerLeg.objects.count(), 1)

    def test_linked_unexpected_cannot_be_changed_or_deleted(self):
        expense = save_record(self.admin, self.profile.pk, UnexpectedExpense, {"name": "Extra", "amount": Decimal("10")})
        TransactionBatch.objects.create(profile=self.profile, unexpected_expense=expense, kind="unexpected", amount=Decimal("10"), occurred_on=date(2026, 10, 18))
        with self.assertRaises(ValidationError):
            save_record(self.admin, self.profile.pk, UnexpectedExpense, {"amount": Decimal("5")}, expense.pk)
        with self.assertRaises(ValidationError):
            delete_record(self.admin, self.profile.pk, UnexpectedExpense, expense.pk)

    def test_reserve_policy_requires_admin_and_valid_range(self):
        with self.assertRaises(PermissionDenied):
            save_record(self.common, self.profile.pk, ReservePolicy, {"coverage_months": 9})
        for months in (5, 13):
            with self.assertRaises(ValidationError):
                save_record(self.admin, self.profile.pk, ReservePolicy, {"coverage_months": months})
        save_record(self.admin, self.profile.pk, ReservePolicy, {"coverage_months": 6})
        save_record(self.admin, self.profile.pk, ReservePolicy, {"coverage_months": 12})
        self.assertEqual(ReservePolicy.objects.get(profile=self.profile).coverage_months, 12)

    def test_due_day_is_enforced_by_service_and_database(self):
        data = {"name": "Mensal", "category": "essential", "amount": Decimal("1"), "due_day": 32}
        with self.assertRaises(ValidationError):
            save_record(self.admin, self.profile.pk, RecurringExpense, data)
        with self.assertRaises(IntegrityError), transaction.atomic():
            RecurringExpense.objects.create(profile=self.profile, **data)

    def test_reserve_manual_target_and_negative_positions_rejected(self):
        with self.assertRaises(ValidationError):
            save_record(self.admin, self.profile.pk, InvestmentPosition, {"name": "Reserva", "category": "reserve", "target_amount": Decimal("10")})
        with self.assertRaises(ValidationError):
            save_record(self.admin, self.profile.pk, InvestmentPosition, {"name": "Meta", "category": "planned", "current_value": Decimal("-1")})

    def test_unlinked_records_can_be_deleted_without_cash_effect(self):
        expense = save_record(self.common, self.profile.pk, UnexpectedExpense, {"name": "Extra", "amount": Decimal("10")})
        delete_record(self.common, self.profile.pk, UnexpectedExpense, expense.pk)
        self.assertFalse(UnexpectedExpense.objects.exists())
        self.assertFalse(TransactionBatch.objects.exists())
