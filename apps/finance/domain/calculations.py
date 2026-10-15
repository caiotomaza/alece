# SPDX-License-Identifier: GPL-3.0-only
"""Cálculos financeiros puros: Decimal, determinísticos e testáveis sem Django.

Renda (fluxo) e saldo bancário (posição) nunca são somados entre si.
"""
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")


def money(value: Decimal | str | int) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def reserve_goal(essential_monthly: Decimal, months: int = 9) -> Decimal:
    if not isinstance(months, int) or not 6 <= months <= 12:
        raise ValueError("Cobertura da reserva deve ser um inteiro entre 6 e 12 meses.")
    if essential_monthly < 0:
        raise ValueError("Despesas essenciais não podem ser negativas.")
    return money(essential_monthly * months)


def allocate_monthly(
    income: Decimal,
    essentials: Decimal,
    strategic: Decimal,
    discretionary: Decimal,
    unexpected_confirmed: Decimal,
    reserve_current: Decimal,
    reserve_target: Decimal,
    weights: tuple[int, int, int] = (1, 1, 1),
) -> dict[str, Decimal]:
    amounts = (
        income, essentials, strategic, discretionary,
        unexpected_confirmed, reserve_current, reserve_target,
    )
    if any(x < 0 for x in amounts):
        raise ValueError("Valores negativos não são aceitos em orçamento/posições.")
    if len(weights) != 3 or any(type(w) is not int or w < 0 for w in weights):
        raise ValueError("Informe três pesos inteiros não negativos.")
    available = max(Decimal("0"), money(income - essentials - strategic - discretionary - unexpected_confirmed))
    reserve_gap = max(Decimal("0"), money(reserve_target - reserve_current))
    reserve_application = min(available, reserve_gap)
    investable_cents = int(((available - reserve_application) / CENT).to_integral_value())
    weight_sum = sum(weights)
    distributed = [0, 0, 0]
    if weight_sum > 0:
        # Largest-remainder method: total distributed matches the available cents exactly.
        numerators = [investable_cents * w for w in weights]
        distributed = [v // weight_sum for v in numerators]
        leftovers = investable_cents - sum(distributed)
        order = sorted(range(3), key=lambda idx: (-(numerators[idx] % weight_sum), idx))
        for i in order[:leftovers]:
            distributed[i] += 1
    return {
        "available_before_reserve": available,
        "reserve": money(reserve_application),
        "development": Decimal(distributed[0]) * CENT,
        "patrimony": Decimal(distributed[1]) * CENT,
        "planned_consumption": Decimal(distributed[2]) * CENT,
        "unallocated": Decimal(investable_cents - sum(distributed)) * CENT,
    }
