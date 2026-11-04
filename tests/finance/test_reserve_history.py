# SPDX-License-Identifier: GPL-3.0-only
"""Regras de histórico completo da reserva, sem depender do pagamento da despesa."""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.finance.models import (
    FinancialProfile, InvestmentPosition, RecurringExpense, ReservePolicy,
    TransactionBatch, UnexpectedExpense, Workspace,
)
from apps.finance.services.metrics import profile_summary


class ReserveHistoryTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="reserve-history")
        workspace = Workspace.objects.create(name="Reserva", created_by=user)
        self.profile = FinancialProfile.objects.create(
            workspace=workspace, name="Principal", monthly_income=Decimal("2300.00"),
        )
        self.other = FinancialProfile.objects.create(workspace=workspace, name="Privado")
        for name, category, amount in (
            ("Essenciais", "essential", "532.90"),
            ("Estratégicas", "strategic", "444.28"),
        ):
            RecurringExpense.objects.create(
                profile=self.profile, name=name, category=category,
                amount=Decimal(amount), due_day=1,
            )
        ReservePolicy.objects.create(profile=self.profile, coverage_months=7)
        InvestmentPosition.objects.create(
            profile=self.profile, name="Reserva", category="reserve",
            current_value=Decimal("2754.71"),
        )

    def add_unexpected(self, year, month, amount, *, profile=None):
        return UnexpectedExpense.objects.create(
            profile=profile or self.profile,
            name="Imprevista", amount=Decimal(amount),
            recorded_on=date(year, month, 10),
        )

    def test_example_all_categories_and_three_historical_months(self):
        self.add_unexpected(2026, 1, "500.00")
        self.add_unexpected(2026, 2, "300.00")
        self.add_unexpected(2026, 3, "200.00")
        self.add_unexpected(2026, 3, "100.00", profile=self.other)
        result = profile_summary(self.profile, date(2026, 11, 1))
        self.assertEqual(result["reserve_recurring_monthly"], Decimal("977.18"))
        self.assertEqual(result["reserve_unexpected_month_count"], 3)
        self.assertEqual(result["reserve_unexpected_monthly"], Decimal("333.33"))
        self.assertEqual(result["reserve_monthly_base"], Decimal("1310.51"))
        self.assertEqual(result["reserve_target"], Decimal("9173.57"))
        self.assertEqual(result["reserve_gap"], Decimal("6418.86"))
        self.assertEqual(result["allocation"]["reserve"], Decimal("1322.82"))

    def test_multiple_expenses_same_month_count_once_and_include_discretionary(self):
        RecurringExpense.objects.create(
            profile=self.profile, name="Discricionária", category="discretionary",
            amount=Decimal("20.00"), due_day=5,
        )
        self.add_unexpected(2024, 1, "100.00")
        self.add_unexpected(2024, 1, "200.00")
        self.add_unexpected(2024, 4, "100.00")
        result = profile_summary(self.profile)
        self.assertEqual(result["reserve_unexpected_month_count"], 2)
        self.assertEqual(result["reserve_unexpected_monthly"], Decimal("200.00"))
        self.assertEqual(result["reserve_target"], Decimal("8380.26"))

    def test_all_available_months_not_fixed_window(self):
        for year in (2024, 2025):
            for month in range(1, 13):
                self.add_unexpected(year, month, "10.00")
        result = profile_summary(self.profile)
        self.assertEqual(result["reserve_unexpected_month_count"], 24)
        self.assertEqual(result["reserve_unexpected_monthly"], Decimal("10.00"))
        self.assertEqual(result["reserve_target"], Decimal("6910.26"))

    def test_no_history_and_inactive_recurring(self):
        RecurringExpense.objects.create(
            profile=self.profile, name="Arquivada", category="essential",
            amount=Decimal("999.00"), due_day=1, is_active=False,
        )
        result = profile_summary(self.profile)
        self.assertEqual(result["reserve_unexpected_month_count"], 0)
        self.assertEqual(result["reserve_unexpected_monthly"], Decimal("0.00"))
        self.assertEqual(result["reserve_target"], Decimal("6840.26"))

    def test_one_unexpected_registration_not_counted_again_after_payment(self):
        expense = self.add_unexpected(2026, 4, "50.00")
        TransactionBatch.objects.create(
            profile=self.profile, unexpected_expense=expense,
            kind=TransactionBatch.Kind.UNEXPECTED, amount=Decimal("50.00"),
            occurred_on=date(2026, 4, 10),
        )
        result = profile_summary(self.profile, date(2026, 4, 1))
        self.assertEqual(result["reserve_unexpected_monthly"], Decimal("50.00"))
        self.assertEqual(result["reserve_target"], Decimal("7190.26"))
        self.assertEqual(result["unexpected_confirmed"], Decimal("50.00"))

    def test_reserve_target_without_known_income(self):
        self.profile.monthly_income = None
        self.profile.save(update_fields=["monthly_income"])
        result = profile_summary(self.profile)
        self.assertEqual(result["reserve_target"], Decimal("6840.26"))
        self.assertIsNone(result["allocation"])
