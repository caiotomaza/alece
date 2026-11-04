# SPDX-License-Identifier: GPL-3.0-only
"""Profile-scoped read model. Calling views must authorize the profile first.

Money is Decimal throughout. bank_balance is the sum of *known* active account
balances, never income; bank_unknown_count identifies the incomplete coverage.
Unexpected registrations and confirmed payments are separate, month scoped.
allocation is None until income and at least one active recurring are known.
"""
from decimal import Decimal, ROUND_HALF_UP
from datetime import date

from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.finance.domain.calculations import (
    allocate_monthly, money, reserve_goal, unexpected_monthly_average,
)
from apps.finance.domain.planning import goal_eta_months
from apps.finance.models import (
    InvestmentPosition, RecurringExpense, ReservePolicy, TransactionBatch, UnexpectedExpense,
)

ZERO = Decimal("0.00")


def aggregate_income_plan(sections):
    """Build a read-only, permission-complete monthly plan for the overview ring."""
    if not sections or any(
        not (section["can_expenses_view"] and section["can_investments_view"])
        or section["summary"].get("income") is None
        or section["summary"].get("allocation") is None
        for section in sections
    ):
        return None
    income = sum((section["summary"]["income"] for section in sections), ZERO)
    if income <= ZERO:
        return None
    descriptors = (
        ("Essenciais (Despesas)", "essential", "#1A7F4B", "expense"),
        ("Discricionárias (Despesas)", "discretionary", "#C79A2B", "expense"),
        ("Imprevisíveis (Despesas)", "unexpected_confirmed", "#D65A4A", "direct"),
        ("Estratégicas (Despesas)", "strategic", "#3D8E75", "expense"),
        ("Desenvolvimento pessoal e profissional (Investimentos)", "development", "#3A7BC2", "allocation"),
        ("Aquisição patrimonial (Investimentos)", "patrimony", "#6D59AF", "allocation"),
        ("Consumo planejado (Investimentos)", "planned_consumption", "#168C8F", "allocation"),
        ("Reserva (Investimentos)", "reserve", "#27694E", "allocation"),
    )
    categories = []
    all_categories = []
    fragments = []
    cursor = Decimal("0")
    for label, key, color, source in descriptors:
        value = sum((
            section["summary"]["recurring_totals"][key] if source == "expense"
            else section["summary"]["allocation"][key] if source == "allocation"
            else section["summary"][key]
            for section in sections
        ), ZERO)
        # Preserva todas as categorias no modelo de leitura; a tabela e o gráfico
        # exibem somente as categorias com valor positivo.
        percent = (value / income * Decimal("100")).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP,
        )
        all_categories.append({
            "label": label, "value": value, "color": color,
            "source": source, "percent": percent,
        })
        if value <= ZERO:
            continue
        end = min(Decimal("100"), cursor + value / income * Decimal("100"))
        start_pct = cursor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        end_pct = end.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if end_pct > start_pct:
            fragments.append(f"{color} {start_pct}% {end_pct}%")
        cursor = end
        categories.append({
            "label": label, "value": value, "color": color,
            "source": source, "percent": percent,
        })
    if cursor < Decimal("100"):
        fragments.append(f"var(--chart-bg) {cursor:.2f}% 100%")
    allocated = sum((entry["value"] for entry in categories), ZERO)
    return {
        "categories": categories,
        "all_categories": all_categories,
        "income": income,
        "allocated": allocated,
        "unallocated": max(ZERO, income - allocated),
        "excess": max(ZERO, allocated - income),
        "donut_css": "conic-gradient(from -90deg, " + ", ".join(fragments) + ")",
    }


def monthly_activity(profile_ids, month, *, kinds, category="all"):
    """Actual confirmed ledger activity over six months for visual history cards."""
    months = []
    index = month.year * 12 + month.month - 1
    for offset in range(5, -1, -1):
        value = index - offset
        months.append(date(value // 12, value % 12 + 1, 1))
    next_index = index + 1
    end = date(next_index // 12, next_index % 12 + 1, 1)
    queryset = TransactionBatch.objects.filter(
        profile_id__in=profile_ids, kind__in=kinds,
        occurred_on__gte=months[0], occurred_on__lt=end,
        reversal__isnull=True,
    )
    if category == "unexpected":
        queryset = queryset.filter(kind=TransactionBatch.Kind.UNEXPECTED)
    elif category in RecurringExpense.Category.values:
        queryset = queryset.filter(kind=TransactionBatch.Kind.RECURRING).filter(
            Q(recurring_expense__category=category)
            | Q(monthly_expense__recurring_expense__category=category)
        )
    totals = {item: ZERO for item in months}
    for row in queryset.values("occurred_on", "amount"):
        occurred = row["occurred_on"].replace(day=1)
        if occurred in totals:
            totals[occurred] += row["amount"]
    peak = max(totals.values(), default=ZERO)
    return {
        "points": [
            {"label": item.strftime("%m/%Y"), "value": total,
             "height": int((total / peak * 100).to_integral_value()) if peak else 0}
            for item, total in totals.items()
        ],
        "has_data": peak > ZERO,
        "total": sum(totals.values(), ZERO),
    }


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
    reserve_recurring = money(sum(totals.values(), ZERO)) if include_expenses else None
    historical_months = []
    if include_expenses and include_investments:
        historical_months = list(
            UnexpectedExpense.objects.filter(profile=profile)
            .annotate(month=TruncMonth("recorded_on"))
            .values("month").annotate(total=Sum("amount"))
            .order_by("month")
        )
    historical_average = (
        unexpected_monthly_average([row["total"] for row in historical_months])
        if include_expenses and include_investments else None
    )
    reserve_monthly_base = (
        money(reserve_recurring + historical_average)
        if historical_average is not None else None
    )
    target = (
        reserve_goal(reserve_monthly_base, coverage)
        if reserve_monthly_base is not None else None
    )
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
        target_value = targets[category]
        progress_pct = None
        gap = None
        if target_value is not None:
            gap = max(ZERO, target_value - investments[category])
            if target_value > ZERO:
                progress_pct = min(
                    Decimal("100.0"),
                    ((investments[category] / target_value) * Decimal("100")).quantize(
                        Decimal("0.1"), rounding=ROUND_HALF_UP,
                    ),
                )
        categories.append({
            "category": category,
            "label": label,
            "current": investments[category],
            "target": target_value,
            "gap": gap,
            "progress_pct": progress_pct,
            "suggestion": suggestion,
            "eta_months": goal_eta_months(target_value, investments[category], suggestion),
        })
    has_known_balance = accounts.filter(balance__isnull=False).exists() if accounts is not None else False
    bank_balance = accounts.aggregate(total=Sum("balance"))["total"] if has_known_balance else None
    return {
        "income": profile.monthly_income if include_income else None,
        "planned_expenses": money(sum(totals.values(), ZERO) + confirmed) if include_expenses else None,
        "investable_monthly": (
            allocation["development"] + allocation["patrimony"]
            + allocation["planned_consumption"] if allocation is not None else None
        ),
        "bank_balance": bank_balance,
        "bank_unknown_count": accounts.filter(balance__isnull=True).count() if accounts is not None else 0,
        "recurring_totals": totals,
        "recurring_total": money(sum(totals.values(), ZERO)),
        "unexpected_pending": pending,
        "unexpected_confirmed": confirmed,
        "applications_confirmed": applications_paid,
        "coverage_months": coverage,
        "reserve_recurring_monthly": reserve_recurring,
        "reserve_unexpected_monthly": historical_average,
        "reserve_unexpected_month_count": len(historical_months),
        "reserve_monthly_base": reserve_monthly_base,
        "reserve_target": target,
        "reserve_current": investments["reserve"],
        "reserve_gap": max(ZERO, target - investments["reserve"]) if target is not None else None,
        "allocation": allocation,
        "investment_totals": investments,
        "investment_categories": categories,
    }
