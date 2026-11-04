# SPDX-License-Identifier: GPL-3.0-only
"""Visual summaries are backed by real Decimal plans and confirmed ledger activity."""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.finance.models import BankAccount, FinancialProfile, RecurringExpense, Workspace, WorkspaceMembership
from apps.finance.services.ledger import transfer
from apps.finance.services.metrics import (
    aggregate_income_plan, monthly_activity, profile_summary,
)
from apps.finance.services.reports import generate_goals_report


class VisualReadModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="chart-admin")
        self.workspace = Workspace.objects.create(name="Synthetic", created_by=self.user)
        WorkspaceMembership.objects.create(
            workspace=self.workspace, user=self.user, role="admin",
        )
        self.profile = FinancialProfile.objects.create(
            workspace=self.workspace, name="Chart", monthly_income=Decimal("100.00"),
        )

    def test_income_ring_uses_monthly_plan_and_preserves_unknown(self):
        month = date(2026, 10, 1)
        RecurringExpense.objects.create(
            profile=self.profile, name="Plan", category="essential",
            amount=Decimal("20.00"), due_day=8,
        )
        section = {
            "can_expenses_view": True, "can_investments_view": True,
            "summary": profile_summary(self.profile, month),
        }
        plan = aggregate_income_plan([section])
        self.assertEqual(plan["income"], Decimal("100.00"))
        self.assertEqual(plan["allocated"], Decimal("100.00"))
        self.assertEqual(plan["categories"][0]["value"], Decimal("20.00"))
        self.assertEqual(plan["categories"][0]["percent"], Decimal("20.0"))
        self.assertIn("conic-gradient", plan["donut_css"])
        self.assertEqual(len(plan["all_categories"]), 8)
        self.assertEqual(plan["all_categories"][0]["label"], "Essenciais (Despesas)")
        self.assertEqual(plan["all_categories"][0]["percent"], Decimal("20.0"))
        self.assertEqual(plan["all_categories"][1]["percent"], Decimal("0.0"))
        self.assertEqual(sum(row["value"] for row in plan["all_categories"]), plan["allocated"])
        self.assertTrue(all(row["value"] > 0 for row in plan["categories"]))
        self.assertTrue(all(row["source"] in ("expense", "direct", "allocation") for row in plan["categories"]))
        section["summary"]["income"] = None
        self.assertIsNone(aggregate_income_plan([section]))

    def test_income_ring_omits_zero_categories_and_preserves_nonzero_labels(self):
        values = {"essential": Decimal("40.00"), "discretionary": Decimal("0.00"),
                  "strategic": Decimal("0.00")}
        section = {
            "can_expenses_view": True, "can_investments_view": True,
            "summary": {
                "income": Decimal("100.00"), "recurring_totals": values,
                "unexpected_confirmed": Decimal("0.00"),
                "allocation": {
                    "development": Decimal("60.00"),
                    "patrimony": Decimal("0.00"),
                    "planned_consumption": Decimal("0.00"),
                    "reserve": Decimal("0.00"),
                },
            },
        }
        plan = aggregate_income_plan([section])
        self.assertEqual([row["label"] for row in plan["categories"]], [
            "Essenciais (Despesas)",
            "Desenvolvimento pessoal e profissional (Investimentos)",
        ])
        self.assertEqual([row["source"] for row in plan["categories"]], ["expense", "allocation"])
        self.assertEqual([row["percent"] for row in plan["categories"]], [
            Decimal("40.0"), Decimal("60.0"),
        ])
        self.assertTrue(all(row["value"] > 0 for row in plan["categories"]))
        self.assertEqual(plan["allocated"], Decimal("100.00"))
        self.assertEqual(plan["unallocated"], Decimal("0.00"))
        self.assertNotIn("#C79A2B", plan["donut_css"])
        self.assertNotIn("#D65A4A", plan["donut_css"])

    def test_income_ring_all_zero_categories_has_empty_legend_and_neutral_ring(self):
        section = {
            "can_expenses_view": True, "can_investments_view": True,
            "summary": {
                "income": Decimal("100.00"),
                "recurring_totals": {
                    "essential": Decimal("0.00"),
                    "discretionary": Decimal("0.00"),
                    "strategic": Decimal("0.00"),
                },
                "unexpected_confirmed": Decimal("0.00"),
                "allocation": {
                    "development": Decimal("0.00"),
                    "patrimony": Decimal("0.00"),
                    "planned_consumption": Decimal("0.00"),
                    "reserve": Decimal("0.00"),
                },
            },
        }
        plan = aggregate_income_plan([section])
        self.assertEqual(plan["categories"], [])
        self.assertEqual(plan["allocated"], Decimal("0.00"))
        self.assertEqual(plan["unallocated"], Decimal("100.00"))
        self.assertIn("var(--chart-bg) 0.00% 100%", plan["donut_css"])

    def test_history_excludes_unconfirmed_registration(self):
        month = date(2026, 10, 1)
        RecurringExpense.objects.create(
            profile=self.profile, name="Unpaid", category="essential",
            amount=Decimal("20.00"), due_day=8,
        )
        expenses = monthly_activity(
            [self.profile.pk], month, kinds=("recurring", "unexpected"),
        )
        self.assertFalse(expenses["has_data"])
        self.assertEqual(expenses["total"], Decimal("0.00"))
        source = BankAccount.objects.create(
            profile=self.profile, name="Source", balance=Decimal("100.00"),
            opening_balance=Decimal("100.00"),
        )
        destination = BankAccount.objects.create(
            profile=self.profile, name="Destination", balance=Decimal("0.00"),
            opening_balance=Decimal("0.00"),
        )
        transfer(
            actor=self.user, profile_id=self.profile.pk,
            source_id=source.pk, destination_id=destination.pk,
            amount=Decimal("25.00"), idempotency_key="chart-transfer",
            occurred_on=date(2026, 10, 10),
        )
        movement = monthly_activity([self.profile.pk], month, kinds=("transfer",))
        self.assertTrue(movement["has_data"])
        self.assertEqual(movement["total"], Decimal("25.00"))
        self.assertEqual(movement["points"][-1]["height"], 100)

    def test_missing_plan_has_unknown_monthly_suggestion(self):
        goals = generate_goals_report(self.profile)
        self.assertIsNone(goals.reserve["monthly_suggestion"])
