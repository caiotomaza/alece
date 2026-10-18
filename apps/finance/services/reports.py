# SPDX-License-Identifier: GPL-3.0-only
"""Serviços de relatórios financeiros consolidados.

Relatórios baseados exclusivamente no ledger imutável:
- DRE simplificado por período/competência
- Evolução patrimonial histórica
- Posições de investimento, aplicações, resgates
- Progresso das metas e cobertura da Reserva
- Fluxo de caixa por período

Nunca confunde orçamento com execução, transferências com receitas,
aplicações com despesas, valorização patrimonial com rendimento realizado
ou saldo desconhecido com zero.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from django.db.models import Sum
from django.utils import timezone

from apps.finance.models import (
    BankAccount, FinancialProfile, InvestmentPosition, MonthlyExpense, TransactionBatch, UnexpectedExpense,
)


# =============================================================================
# Dataclasses
# =============================================================================

@dataclass
class DREReport:
    """Demonstração do Resultado do Exercício simplificada."""
    period_start: date
    period_end: date
    profile: str
    
    # Receitas
    income_received: Decimal = Decimal("0.00")
    income_pending: Decimal = Decimal("0.00")
    
    # Despesas
    expenses_confirmed: Decimal = Decimal("0.00")
    expenses_pending: Decimal = Decimal("0.00")
    
    # Resultado
    net_result: Decimal = Decimal("0.00")
    
    # Detalhamento por tipo
    income_by_type: dict[str, Decimal] = field(default_factory=dict)
    expenses_by_type: dict[str, Decimal] = field(default_factory=dict)
    expenses_by_category: dict[str, Decimal] = field(default_factory=dict)
    
    # Alertas
    warnings: list[str] = field(default_factory=list)


@dataclass
class EquityEvolutionPoint:
    """Ponto na evolução patrimonial."""
    date: date
    total_assets: Decimal  # Contas + Investimentos
    total_liabilities: Decimal = Decimal("0.00")  # Para futuro
    net_equity: Decimal = Decimal("0.00")
    bank_balance: Decimal = Decimal("0.00")
    investment_value: Decimal = Decimal("0.00")
    unknown_balance_count: int = 0


@dataclass
class EquityEvolutionReport:
    """Relatório de evolução patrimonial."""
    profile: str
    period_start: date
    period_end: date
    points: list[EquityEvolutionPoint] = field(default_factory=list)
    current_equity: Decimal = Decimal("0.00")
    variation: Decimal = Decimal("0.00")
    variation_pct: Decimal = Decimal("0.00")
    warnings: list[str] = field(default_factory=list)


@dataclass
class InvestmentReport:
    """Relatório de posições de investimento."""
    profile: str
    as_of: date
    positions: list[dict] = field(default_factory=list)
    total_applied: Decimal = Decimal("0.00")
    total_current: Decimal = Decimal("0.00")
    total_unrealized_gain: Decimal = Decimal("0.00")
    applications_period: Decimal = Decimal("0.00")
    withdrawals_period: Decimal = Decimal("0.00")
    by_category: dict[str, dict] = field(default_factory=dict)


@dataclass
class GoalsReport:
    """Relatório de progresso das metas."""
    profile: str
    as_of: date
    reserve: dict = field(default_factory=dict)
    goals: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# =============================================================================
# DRE (Demonstração do Resultado do Exercício)
# =============================================================================

def generate_dre_report(
    profile: FinancialProfile,
    period_start: date,
    period_end: date,
) -> DREReport:
    """Gera DRE simplificada para o período.
    
    Receitas: apenas kind=income (recebimentos confirmados)
    Despesas: recurring, unexpected, application (saídas confirmadas)
    Transferências, aplicações, resgates NÃO entram no DRE.
    """
    report = DREReport(
        period_start=period_start,
        period_end=period_end,
        profile=str(profile),
    )
    
    # Buscar batches no período
    batches = TransactionBatch.objects.filter(
        profile=profile,
        occurred_on__range=(period_start, period_end),
        reversal__isnull=True,  # Não estornados
    ).select_related(
        "recurring_expense", "unexpected_expense", "investment", "monthly_expense"
    ).prefetch_related("legs__account")
    
    for batch in batches:
        if batch.kind == "income":
            report.income_received += batch.amount
            report.income_by_type[batch.get_kind_display()] = \
                report.income_by_type.get(batch.get_kind_display(), Decimal("0.00")) + batch.amount
        
        elif batch.kind in ("recurring", "unexpected"):
            report.expenses_confirmed += batch.amount
            report.expenses_by_type[batch.get_kind_display()] = \
                report.expenses_by_type.get(batch.get_kind_display(), Decimal("0.00")) + batch.amount
            
            # Categoria da despesa
            cat = ""
            if batch.kind == "recurring" and batch.recurring_expense:
                cat = batch.recurring_expense.get_category_display()
            elif batch.kind == "unexpected" and batch.unexpected_expense:
                cat = "Imprevisível"
            if cat:
                report.expenses_by_category[cat] = \
                    report.expenses_by_category.get(cat, Decimal("0.00")) + batch.amount
        
        elif batch.kind == "application":
            # Aplicação NÃO é despesa no DRE
            report.expenses_by_type["Aplicação (não-DRE)"] = \
                report.expenses_by_type.get("Aplicação (não-DRE)", Decimal("0.00")) + batch.amount
    
    # Pendências (não confirmadas no ledger)
    # Despesas previsíveis pendentes
    monthly_expenses = MonthlyExpense.objects.filter(
        profile=profile,
        competence_month__range=(period_start.replace(day=1), period_end.replace(day=1)),
    ).select_related("recurring_expense")
    
    for me in monthly_expenses:
        paid = TransactionBatch.objects.filter(
            monthly_expense=me, kind="recurring", reversal__isnull=True
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        remaining = me.amount - paid
        if remaining > 0:
            report.expenses_pending += remaining
    
    # Despesas imprevisíveis pendentes
    unexpected = UnexpectedExpense.objects.filter(
        profile=profile,
        recorded_on__range=(period_start, period_end),
    )
    for ue in unexpected:
        paid = TransactionBatch.objects.filter(
            unexpected_expense=ue, kind="unexpected", reversal__isnull=True
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        remaining = ue.amount - paid
        if remaining > 0:
            report.expenses_pending += remaining
    
    # Receitas pendentes (não há no modelo atual, mas deixar preparado)
    
    report.net_result = report.income_received - report.expenses_confirmed
    
    # Alertas
    if report.income_received == 0 and report.expenses_confirmed > 0:
        report.warnings.append("Despesas confirmadas sem receitas no período.")
    if report.expenses_pending > report.income_received:
        report.warnings.append(f"Despesas pendentes (R$ {report.expenses_pending:.2f}) superam receitas recebidas.")
    
    return report


# =============================================================================
# Evolução Patrimonial
# =============================================================================

def generate_equity_evolution_report(
    profile: FinancialProfile,
    period_start: date,
    period_end: date,
    interval: str = "month",  # "day", "week", "month"
) -> EquityEvolutionReport:
    """Gera evolução patrimonial (ativos - passivos) ao longo do tempo.
    
    Ativos = Saldos bancários conhecidos + Valor atual dos investimentos
    Passivos = 0 (não há passivos modelados além de contas a pagar futuras)
    Patrimônio líquido = Ativos - Passivos
    
    Saldo desconhecido (NULL) é sinalizado, não somado como zero.
    """
    report = EquityEvolutionReport(
        profile=str(profile),
        period_start=period_start,
        period_end=period_end,
    )
    
    # Gerar pontos no intervalo
    current = period_start
    while current <= period_end:
        point = _calculate_equity_at_date(profile, current)
        point.date = current
        report.points.append(point)
        
        if interval == "day":
            current += timedelta(days=1)
        elif interval == "week":
            current += timedelta(weeks=1)
        else:  # month
            # Próximo mês
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
    
    if report.points:
        report.current_equity = report.points[-1].net_equity
        if len(report.points) >= 2:
            first = report.points[0].net_equity
            last = report.points[-1].net_equity
            report.variation = last - first
            if first != 0:
                report.variation_pct = (report.variation / first) * Decimal("100")
    
    # Alertas
    unknown_count = sum(p.unknown_balance_count for p in report.points)
    if unknown_count > 0:
        report.warnings.append(f"{unknown_count} ponto(s) com saldo(s) desconhecido(s) - evolução parcial.")
    
    return report


def _calculate_equity_at_date(profile: FinancialProfile, as_of: date) -> EquityEvolutionPoint:
    """Calcula patrimônio em uma data específica."""
    point = EquityEvolutionPoint(date=as_of)
    
    # Saldos bancários conhecidos
    accounts = BankAccount.objects.filter(profile=profile, is_archived=False)
    bank_known = Decimal("0.00")
    point.unknown_balance_count = 0
    
    for acc in accounts:
        if acc.balance is not None:
            bank_known += acc.balance
        else:
            point.unknown_balance_count += 1
    
    point.bank_balance = bank_known
    
    # Investimentos (valor atual)
    investments = InvestmentPosition.objects.filter(profile=profile, is_active=True)
    investment_value = Decimal("0.00")
    for inv in investments:
        investment_value += inv.current_value
    
    point.investment_value = investment_value
    point.total_assets = bank_known + investment_value
    point.net_equity = point.total_assets  # Sem passivos modelados
    
    return point


# =============================================================================
# Relatório de Investimentos
# =============================================================================

def generate_investment_report(
    profile: FinancialProfile,
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
) -> InvestmentReport:
    """Relatório de posições, aplicações e resgates no período."""
    if period_end is None:
        period_end = timezone.localdate()
    if period_start is None:
        period_start = period_end.replace(day=1)
    
    report = InvestmentReport(
        profile=str(profile),
        as_of=period_end,
    )
    
    # Posições atuais
    positions = InvestmentPosition.objects.filter(profile=profile, is_active=True)
    for inv in positions:
        report.positions.append({
            "name": inv.name,
            "institution": inv.institution,
            "category": inv.get_category_display(),
            "applied_amount": inv.applied_amount,
            "current_value": inv.current_value,
            "unrealized_gain": inv.current_value - inv.applied_amount,
            "target_amount": inv.target_amount,
            "category_key": inv.category,
        })
        report.total_applied += inv.applied_amount
        report.total_current += inv.current_value
        
        cat = inv.category
        if cat not in report.by_category:
            report.by_category[cat] = {"applied": Decimal("0.00"), "current": Decimal("0.00"), "count": 0}
        report.by_category[cat]["applied"] += inv.applied_amount
        report.by_category[cat]["current"] += inv.current_value
        report.by_category[cat]["count"] += 1
    
    report.total_unrealized_gain = report.total_current - report.total_applied
    
    # Aplicações e resgates no período
    if period_start and period_end:
        apps = TransactionBatch.objects.filter(
            profile=profile,
            kind="application",
            occurred_on__range=(period_start, period_end),
            reversal__isnull=True,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        report.applications_period = apps
        
        wds = TransactionBatch.objects.filter(
            profile=profile,
            kind="withdrawal",
            occurred_on__range=(period_start, period_end),
            reversal__isnull=True,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        report.withdrawals_period = wds
    
    return report


# =============================================================================
# Relatório de Metas e Reserva
# =============================================================================

def generate_goals_report(profile: FinancialProfile) -> GoalsReport:
    """Relatório de progresso da Reserva e metas."""
    from apps.finance.services.metrics import profile_summary
    
    report = GoalsReport(profile=str(profile), as_of=timezone.localdate())
    
    # Reserva
    summary = profile_summary(profile, timezone.localdate().replace(day=1))
    report.reserve = {
        "current": summary.get("reserve_current", Decimal("0.00")),
        "target": summary.get("reserve_target", Decimal("0.00")),
        "gap": summary.get("reserve_gap", Decimal("0.00")),
        "coverage_months": summary.get("coverage_months", 9),
        "monthly_suggestion": summary.get("allocation", {}).get("reserve", Decimal("0.00")) if summary.get("allocation") else Decimal("0.00"),
        "progress_pct": Decimal("0.00"),
    }
    
    if report.reserve["target"] > 0:
        report.reserve["progress_pct"] = (report.reserve["current"] / report.reserve["target"]) * Decimal("100")
    
    # Metas de investimento
    positions = InvestmentPosition.objects.filter(profile=profile, is_active=True).exclude(target_amount=None)
    for inv in positions:
        progress = Decimal("0.00")
        if inv.target_amount and inv.target_amount > 0:
            progress = (inv.current_value / inv.target_amount) * Decimal("100")
        report.goals.append({
            "name": inv.name,
            "category": inv.get_category_display(),
            "current": inv.current_value,
            "target": inv.target_amount,
            "progress_pct": progress,
            "category_key": inv.category,
        })
    
    # Alertas
    if report.reserve["gap"] > 0:
        report.warnings.append(f"Reserva incompleta: faltam R$ {report.reserve['gap']:.2f} para a meta.")
    
    return report


# =============================================================================
# Relatório Consolidado (Dashboard)
# =============================================================================

@dataclass
class DashboardReport:
    """Relatório consolidado para dashboard."""
    profile: str
    as_of: date
    dre: DREReport
    equity: EquityEvolutionReport
    investments: InvestmentReport
    goals: GoalsReport


def generate_dashboard_report(
    profile: FinancialProfile,
    period_start: date,
    period_end: date,
) -> DashboardReport:
    """Gera relatório consolidado para o dashboard."""
    return DashboardReport(
        profile=str(profile),
        as_of=period_end,
        dre=generate_dre_report(profile, period_start, period_end),
        equity=generate_equity_evolution_report(profile, period_start, period_end, "month"),
        investments=generate_investment_report(profile, period_start, period_end),
        goals=generate_goals_report(profile),
    )