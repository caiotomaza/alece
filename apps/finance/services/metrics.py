# SPDX-License-Identifier: GPL-3.0-only
"""Profile-scoped read model. Calling views must authorize the profile first.

Money is Decimal throughout. bank_balance is the sum of *known* active account
balances, never income; bank_unknown_count identifies the incomplete coverage.
Unexpected registrations and confirmed payments are separate, month scoped.
allocation is None until income and at least one active recurring are known.
"""
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from apps.finance.domain.calculations import allocate_monthly, money, reserve_goal
from apps.finance.domain.planning import goal_eta_months
from apps.finance.models import (
    InvestmentPosition, RecurringExpense, ReservePolicy, TransactionBatch, UnexpectedExpense,
)

ZERO = Decimal("0.00")


def profile_summary(profile, month=None, *, include_accounts=True, include_expenses=True,
                    include_investments=True, include_income=True):
    month = month or timezone.localdate()
    accounts = profile.accounts.filter(is_archived=False) if include_accounts else None
    recurring = (RecurringExpense.objects.filter(profile=profile, is_active=True)
                 if include_expenses else RecurringExpense.objects.none())
    totals = {category: ZERO for category in RecurringExpense.Category.values}
    for row in recurring.values("category").annotate(total=Sum("amount")):
        totals[row["category"]] = row["total"]
    unexpected = (UnexpectedExpense.objects.filter(
        profile=profile, recorded_on__year=month.year, recorded_on__month=month.month,
    ) if include_expenses else UnexpectedExpense.objects.none())
    month_scope = (
        Q(competence_month__year=month.year, competence_month__month=month.month) |
        Q(competence_month__isnull=True, occurred_on__year=month.year,
          occurred_on__month=month.month)
    )
    payments = (TransactionBatch.objects.filter(
        month_scope, profile=profile, kind=TransactionBatch.Kind.UNEXPECTED,
        reversal__isnull=True,
    ) if include_expenses else TransactionBatch.objects.none())
    confirmed = payments.aggregate(total=Sum("amount"))["total"] or ZERO
    applications_paid = (TransactionBatch.objects.filter(
        profile=profile, kind=TransactionBatch.Kind.APPLICATION, reversal__isnull=True,
        occurred_on__year=month.year, occurred_on__month=month.month,
    ).aggregate(total=Sum("amount"))["total"] or ZERO) if include_investments else ZERO
    # Subtract linked payments from registration amounts only for the pending display.
    pending = ZERO
    for expense in unexpected:
        paid = expense.transactionbatch_set.filter(kind=TransactionBatch.Kind.UNEXPECTED, reversal__isnull=True).aggregate(total=Sum("amount"))["total"] or ZERO
        pending += max(ZERO, expense.amount - paid)
    positions = (InvestmentPosition.objects.filter(profile=profile, is_active=True)
                 if include_investments else InvestmentPosition.objects.none())
    investments = {category: ZERO for category in InvestmentPosition.Category.values}
    targets = {category: None for category in InvestmentPosition.Category.values}
    for row in positions.values("category").annotate(current=Sum("current_value"), target=Sum("target_amount")):
        investments[row["category"]] = row["current"]
        targets[row["category"]] = row["target"]
    policy = ReservePolicy.objects.filter(profile=profile).first() if include_investments else None
    coverage = policy.coverage_months if policy else 9
    target = reserve_goal(totals["essential"], coverage) if include_expenses and include_investments else None
    targets["reserve"] = target
    allocation = None
    if (include_income and include_expenses and include_investments
            and profile.monthly_income is not None and recurring.exists()):
        allocation = allocate_monthly(
            profile.monthly_income, totals["essential"], totals["strategic"],
            totals["discretionary"], confirmed + applications_paid,
            investments["reserve"], target,
        )
    categories = []
    for category, label in InvestmentPosition.Category.choices:
        allocation_key = "planned_consumption" if category == "planned" else category
        suggestion = allocation[allocation_key] if allocation is not None else None
        categories.append({"category": category, "label": label, "current": investments[category], "target": targets[category], "suggestion": suggestion, "eta_months": goal_eta_months(targets[category], investments[category], suggestion)})
    has_known_balance = accounts.filter(balance__isnull=False).exists() if accounts is not None else False
    bank_balance = accounts.aggregate(total=Sum("balance"))["total"] if has_known_balance else None
    return {
        "income": profile.monthly_income if include_income else None,
        "bank_balance": bank_balance,
        "bank_unknown_count": accounts.filter(balance__isnull=True).count() if accounts is not None else 0,
        "recurring_totals": totals,
        "recurring_total": money(sum(totals.values(), ZERO)),
        "unexpected_pending": pending,
        "unexpected_confirmed": confirmed,
        "applications_confirmed": applications_paid,
        "coverage_months": coverage,
        "reserve_target": target,
        "reserve_current": investments["reserve"],
        "reserve_gap": max(ZERO, target - investments["reserve"]) if target is not None else None,
        "allocation": allocation,
        "investment_totals": investments,
        "investment_categories": categories,
    }
