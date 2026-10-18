# SPDX-License-Identifier: GPL-3.0-only
from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_CEILING


def monthly_due_date(month: date, due_day: int) -> date:
    if type(due_day) is not int or not 1 <= due_day <= 31:
        raise ValueError("Dia deve estar entre 1 e 31.")
    return month.replace(day=min(due_day, monthrange(month.year, month.month)[1]))


def goal_eta_months(target, current, monthly_suggestion):
    """No yield assumption; None means insufficient data or no positive contribution."""
    if target is None:
        return None
    gap = max(Decimal("0.00"), target - current)
    if gap == 0:
        return 0
    if monthly_suggestion is None or monthly_suggestion <= 0:
        return None
    return int((gap / monthly_suggestion).to_integral_value(rounding=ROUND_CEILING))
