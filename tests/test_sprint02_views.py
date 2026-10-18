# SPDX-License-Identifier: GPL-3.0-only
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.finance.models import (
    BankAccount, FinancialProfile, InvestmentPosition, RecurringExpense,
    ReservePolicy, TransactionBatch, UnexpectedExpense, Workspace, WorkspaceMembership,
)
from apps.finance.services.metrics import profile_summary


class Sprint02ViewsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username="sprint-admin")
        self.other = User.objects.create_user(username="sprint-other")
        self.workspace = Workspace.objects.create(name="Casa", created_by=self.admin)
        self.foreign_ws = Workspace.objects.create(name="Outra", created_by=self.other)
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.admin, role="admin")
        WorkspaceMembership.objects.create(workspace=self.foreign_ws, user=self.other, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.workspace, name="Pessoal")
        self.foreign_profile = FinancialProfile.objects.create(workspace=self.foreign_ws, name="Privado")
        self.client.force_login(self.admin)

    def p(self, name, profile=None):
        return reverse(f"finance:{name}", args=[(profile or self.profile).pk])

    def w(self, name, workspace=None):
        return reverse(f"finance:{name}", args=[(workspace or self.workspace).pk])

    def test_month_filter_is_scoped_to_authorized_active_profiles(self):
        visible = FinancialProfile.objects.create(workspace=self.workspace, name="Visível")
        FinancialProfile.objects.create(workspace=self.workspace, name="Arquivado", is_archived=True)
        for section in ("overview", "expenses", "investments"):
            response = self.client.get(self.w(section))
            self.assertContains(response, "Pessoal")
            self.assertContains(response, "Visível")
            self.assertNotContains(response, "Privado")
            self.assertNotContains(response, "Arquivado")
            selected = self.client.get(self.w(section), {"profiles": [visible.pk], "month": "2026-02"})
            self.assertContains(selected, "Visível")
            self.assertEqual([item["profile"].pk for item in selected.context["sections"]], [visible.pk])
            self.assertEqual(selected.context["month"], date(2026, 2, 1))
            self.assertEqual(self.client.get(self.w(section), {
                "profiles": [self.foreign_profile.pk], "month": "2026-02",
            }).status_code, 400)
            self.assertEqual(self.client.get(self.w(section), {"month": "invalid"}).status_code, 400)
            self.assertEqual(self.client.get(self.w(section, self.foreign_ws)).status_code, 403)

    def test_income_edit_zero_clear_and_no_cash_movement(self):
        account = BankAccount.objects.create(profile=self.profile, name="Banco", balance=Decimal("30"))
        for value, expected in (("0", Decimal("0")), ("100.51", Decimal("100.51")), ("", None)):
            response = self.client.post(self.p("income-edit"), {"monthly_income": value})
            self.assertRedirects(response, self.p("profile-detail"))
            self.profile.refresh_from_db()
            self.assertEqual(self.profile.monthly_income, expected)
        account.refresh_from_db()
        self.assertEqual(account.balance, Decimal("30"))
        self.assertEqual(TransactionBatch.objects.count(), 0)
        self.assertEqual(self.client.post(self.p("income-edit", self.foreign_profile), {
            "monthly_income": "100",
        }).status_code, 403)

    def test_profile_archive_and_reactivate(self):
        url = self.p("profile-edit")
        self.assertRedirects(self.client.post(url, {
            "name": "Pessoal", "emoji": "", "monthly_income": "", "is_archived": "on",
        }), self.p("profile-detail"))
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.is_archived)
        self.assertNotContains(self.client.get(self.w("overview")), "Pessoal")
        self.assertEqual(self.client.get(self.p("income-edit")).status_code, 403)
        self.assertRedirects(self.client.post(url, {
            "name": "Pessoal", "emoji": "", "monthly_income": "",
        }), self.p("profile-detail"))
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.is_archived)

    def test_recurring_create_edit_archive_delete_and_due_date(self):
        create = self.p("recurring-create")
        response = self.client.post(create, {
            "name": "Aluguel", "category": "essential", "amount": "10.01", "due_day": "31",
        })
        self.assertRedirects(response, self.w("expenses"))
        expense = RecurringExpense.objects.get(profile=self.profile)
        response = self.client.get(self.w("expenses"), {"month": "2026-02"})
        self.assertContains(response, "28/02/2026")
        self.assertContains(response, "10,01")
        self.assertEqual(self.client.post(reverse(
            "finance:recurring-edit", args=[self.profile.pk, expense.pk]), {
                "name": "Aluguel", "category": "essential", "amount": "11.00",
                "due_day": "31", "is_active": "",
            }).status_code, 302)
        expense.refresh_from_db()
        self.assertFalse(expense.is_active)
        delete = reverse("finance:recurring-delete", args=[self.profile.pk, expense.pk])
        self.assertEqual(self.client.post(delete).status_code, 400)
        self.assertTrue(RecurringExpense.objects.filter(pk=expense.pk).exists())
        self.assertRedirects(self.client.post(delete, {"confirm": "yes"}), self.w("expenses"))
        self.assertFalse(RecurringExpense.objects.filter(pk=expense.pk).exists())
        self.assertEqual(TransactionBatch.objects.count(), 0)

    def test_unexpected_month_and_server_date(self):
        with patch("apps.finance.services.records.timezone.localdate", return_value=date(2026, 10, 18)):
            response = self.client.post(self.p("unexpected-create"), {"name": "Conserto", "amount": "12.34", "recorded_on": "2000-01-01"})
        self.assertRedirects(response, self.w("expenses"))
        expense = UnexpectedExpense.objects.get(profile=self.profile)
        self.assertEqual(expense.recorded_on, date(2026, 10, 18))
        self.assertContains(self.client.get(self.w("expenses"), {"month": "2026-10"}), "Conserto")
        self.assertNotContains(self.client.get(self.w("expenses"), {"month": "2026-09"}), "Conserto")
        self.assertEqual(TransactionBatch.objects.count(), 0)

    def test_investment_categories_optional_target_and_reserve_policy(self):
        for category in ("development", "patrimony", "planned", "reserve"):
            response = self.client.post(self.p("investment-create"), {
                "name": category, "category": category, "applied_amount": "1.01",
                "current_value": "1.02", "target_amount": "" if category == "reserve" else "10",
            })
            self.assertEqual(response.status_code, 302, response.content[:300])
        response = self.client.post(self.p("investment-create"), {
            "name": "invalid", "category": "reserve", "applied_amount": "0",
            "current_value": "0", "target_amount": "20",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "calculada automaticamente")
        self.assertEqual(InvestmentPosition.objects.filter(profile=self.profile).count(), 4)
        for months in (6, 9, 12):
            self.assertRedirects(self.client.post(self.p("reserve-edit"), {
                "coverage_months": months,
            }), self.w("investments"))
            self.assertEqual(ReservePolicy.objects.get(profile=self.profile).coverage_months, months)
        self.assertEqual(self.client.post(self.p("reserve-edit"), {"coverage_months": 5}).status_code, 200)

    def test_overview_does_not_add_balance_to_income_or_merge_private_profile(self):
        self.profile.monthly_income = Decimal("100.00")
        self.profile.save(update_fields=["monthly_income"])
        BankAccount.objects.create(profile=self.profile, name="Banco", balance=Decimal("50.00"))
        BankAccount.objects.create(profile=self.foreign_profile, name="Oculta", balance=Decimal("900.00"))
        response = self.client.get(self.w("overview"))
        self.assertEqual(response.context["known_income"], Decimal("100.00"))
        self.assertEqual(response.context["bank_balance"], Decimal("50.00"))
        self.assertNotContains(response, "Oculta")


class FinancialSummaryTests(TestCase):
    def test_reserve_and_monthly_budget_use_cents_without_double_counting_pending(self):
        user = get_user_model().objects.create_user(username="metrics")
        ws = Workspace.objects.create(name="Casa", created_by=user)
        profile = FinancialProfile.objects.create(
            workspace=ws, name="Pessoal", monthly_income=Decimal("100.00"),
        )
        BankAccount.objects.create(profile=profile, name="Banco", balance=Decimal("999.99"))
        BankAccount.objects.create(profile=profile, name="Desconhecido")
        RecurringExpense.objects.create(profile=profile, name="Essencial", category="essential", amount=Decimal("10.01"), due_day=31)
        RecurringExpense.objects.create(profile=profile, name="Estratégico", category="strategic", amount=Decimal("5.00"), due_day=1)
        InvestmentPosition.objects.create(profile=profile, name="Reserva", category="reserve", current_value=Decimal("1.00"))
        ReservePolicy.objects.create(profile=profile, coverage_months=9)
        expense = UnexpectedExpense.objects.create(profile=profile, name="Extra", amount=Decimal("12.34"), recorded_on=date(2026, 10, 18))
        TransactionBatch.objects.create(profile=profile, kind="unexpected", unexpected_expense=expense, amount=Decimal("2.34"), occurred_on=date(2026, 10, 18))
        summary = profile_summary(profile, date(2026, 10, 1))
        self.assertEqual(summary["income"], Decimal("100.00"))
        self.assertEqual(summary["bank_balance"], Decimal("999.99"))
        self.assertEqual(summary["bank_unknown_count"], 1)
        self.assertEqual(summary["unexpected_pending"], Decimal("10.00"))
        self.assertEqual(summary["unexpected_confirmed"], Decimal("2.34"))
        self.assertEqual(summary["reserve_target"], Decimal("90.09"))
        self.assertEqual(summary["reserve_gap"], Decimal("89.09"))
        self.assertEqual(summary["allocation"]["reserve"], Decimal("82.65"))
        self.assertEqual(summary["allocation"]["available_before_reserve"], Decimal("82.65"))
        self.assertEqual(sum((summary["allocation"][k] for k in (
            "reserve", "development", "patrimony", "planned_consumption", "unallocated",
        )), Decimal("0")), Decimal("82.65"))

    def test_completed_reserve_has_zero_suggestion_and_stays_visible(self):
        user = get_user_model().objects.create_user(username="full-reserve")
        ws = Workspace.objects.create(name="Casa", created_by=user)
        profile = FinancialProfile.objects.create(workspace=ws, name="Pessoal", monthly_income=Decimal("100"))
        RecurringExpense.objects.create(profile=profile, name="Casa", category="essential", amount=Decimal("10"), due_day=1)
        InvestmentPosition.objects.create(profile=profile, name="Reserva", category="reserve", current_value=Decimal("90"))
        summary = profile_summary(profile)
        self.assertEqual(summary["reserve_gap"], Decimal("0"))
        self.assertEqual(summary["allocation"]["reserve"], Decimal("0"))
        self.assertEqual(summary["investment_categories"][3]["eta_months"], 0)
