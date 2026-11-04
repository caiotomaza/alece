# SPDX-License-Identifier: GPL-3.0-only
"""Read-only monthly obligations. Payments live exclusively in the ledger."""
from decimal import Decimal

from django.db.models import Sum

from apps.finance.domain.planning import monthly_due_date
from apps.finance.models import (
    InvestmentPosition, MonthlyExpense, MonthlyInvestmentPlan, RecurringExpense,
    TransactionBatch, UnexpectedExpense,
)

ZERO = Decimal("0.00")


def paid_for_recurring(expense, month):
    return TransactionBatch.objects.filter(
        recurring_expense=expense, competence_month=month, kind="recurring",
        reversal__isnull=True,
    ).aggregate(total=Sum("amount"))["total"] or ZERO


def paid_for_unexpected(expense):
    return TransactionBatch.objects.filter(
        unexpected_expense=expense, kind="unexpected", reversal__isnull=True,
    ).aggregate(total=Sum("amount"))["total"] or ZERO


def recurring_due(expense, month):
    snapshot = MonthlyExpense.objects.filter(
        recurring_expense=expense, competence_month=month,
    ).first()
    return snapshot.amount if snapshot else expense.amount


def application_due(position, month, summary=None):
    plan = MonthlyInvestmentPlan.objects.filter(
        investment=position, competence_month=month,
    ).first()
    if plan:
        return plan.amount, plan
    if summary is None:
        from apps.finance.services.metrics import profile_summary
        summary = profile_summary(position.profile, month)
    allocation = summary["allocation"]
    if allocation is None:
        return ZERO, None
    key = "planned_consumption" if position.category == "planned" else position.category
    return allocation[key], None


def paid_for_application(plan):
    if plan is None:
        return ZERO
    return TransactionBatch.objects.filter(
        monthly_investment_plan=plan, kind="application", reversal__isnull=True,
    ).aggregate(total=Sum("amount"))["total"] or ZERO


def monthly_items(profile, month, *, include_applications=False, summary=None):
    items = []
    for expense in RecurringExpense.objects.filter(profile=profile, is_active=True).order_by(
        "due_day", "pk",
    ):
        due = recurring_due(expense, month)
        paid = paid_for_recurring(expense, month)
        items.append({
            "kind": "recurring", "object": expense, "due": due, "paid": paid,
            "remaining": max(ZERO, due - paid), "due_on": monthly_due_date(month, expense.due_day),
        })
    for expense in UnexpectedExpense.objects.filter(
        profile=profile, recorded_on__year=month.year, recorded_on__month=month.month,
    ).order_by("recorded_on", "pk"):
        paid = paid_for_unexpected(expense)
        items.append({
            "kind": "unexpected", "object": expense, "due": expense.amount,
            "paid": paid, "remaining": max(ZERO, expense.amount - paid),
            "due_on": expense.recorded_on,
        })
    if include_applications:
        positions = InvestmentPosition.objects.filter(profile=profile, is_active=True).order_by("pk")
        seen_categories = set()
        for position in positions:
            if position.category in seen_categories:
                continue
            seen_categories.add(position.category)
            due, plan = application_due(position, month, summary)
            if due <= ZERO:
                continue
            paid = paid_for_application(plan)
            items.append({
                "kind": "application", "object": position, "due": due, "paid": paid,
                "remaining": max(ZERO, due - paid), "due_on": month,
            })
    return items
