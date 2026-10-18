# SPDX-License-Identifier: GPL-3.0-only
"""Views para relatórios financeiros consolidados."""
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse

from apps.core.permissions import require_module, user_can_module
from apps.finance.services.reports import (
    generate_dashboard_report, generate_dre_report, generate_equity_evolution_report,
    generate_investment_report, generate_goals_report,
)


# =============================================================================
# Helpers
# =============================================================================

def _reports_return_url(workspace_id):
    return reverse("finance:overview", args=[workspace_id])


def _get_period(request, default_months=12):
    """Extrai período da request ou usa padrão."""
    period_end_str = request.GET.get("period_end")
    period_start_str = request.GET.get("period_start")
    
    if period_end_str:
        try:
            period_end = date.fromisoformat(period_end_str)
        except ValueError:
            period_end = date.today()
    else:
        period_end = date.today()
    
    if period_start_str:
        try:
            period_start = date.fromisoformat(period_start_str)
        except ValueError:
            period_start = period_end.replace(day=1) - timedelta(days=365)
    else:
        period_start = period_end.replace(day=1) - timedelta(days=365)
    
    return period_start, period_end


# =============================================================================
# Dashboard de Relatórios
# =============================================================================

@login_required
def reports_dashboard(request, workspace_id):
    """Dashboard consolidado de relatórios."""
    profile = require_module(request.user, workspace_id, "overview", "view")
    require_module(request.user, workspace_id, "expenses", "view")
    require_module(request.user, workspace_id, "investments", "view")
    
    period_start, period_end = _get_period(request)
    
    # Gerar relatórios
    dashboard = None
    if user_can_module(request.user, profile.pk, "overview", "view") and \
       user_can_module(request.user, profile.pk, "expenses", "view") and \
       user_can_module(request.user, profile.pk, "investments", "view"):
        dashboard = generate_dashboard_report(profile, period_start, period_end)
    
    profiles = profile.workspace.profiles.filter(is_archived=False)
    
    return render(request, "finance/reports_dashboard.html", {
        "workspace": profile.workspace,
        "profile": profile,
        "profiles": profiles,
        "dashboard": dashboard,
        "period_start": period_start,
        "period_end": period_end,
        "can_view_dre": user_can_module(request.user, profile.pk, "expenses", "view"),
        "can_view_investments": user_can_module(request.user, profile.pk, "investments", "view"),
        "cancel_url": _reports_return_url(workspace_id),
    })


# =============================================================================
# DRE (Demonstração do Resultado do Exercício)
# =============================================================================

@login_required
def dre_report(request, workspace_id, profile_id):
    """DRE simplificada por período."""
    profile = require_module(request.user, profile_id, "expenses", "view")
    require_module(request.user, profile_id, "overview", "view")
    
    period_start, period_end = _get_period(request)
    
    dre = generate_dre_report(profile, period_start, period_end)
    
    return render(request, "finance/reports_dre.html", {
        "workspace": profile.workspace,
        "profile": profile,
        "dre": dre,
        "period_start": period_start,
        "period_end": period_end,
        "cancel_url": _reports_return_url(workspace_id),
    })


# =============================================================================
# Evolução Patrimonial
# =============================================================================

@login_required
def equity_evolution_report(request, workspace_id, profile_id):
    """Evolução patrimonial histórica."""
    profile = require_module(request.user, profile_id, "overview", "view")
    require_module(request.user, profile_id, "accounts", "view")
    require_module(request.user, profile_id, "investments", "view")
    
    period_start, period_end = _get_period(request)
    interval = request.GET.get("interval", "month")
    
    equity = generate_equity_evolution_report(profile, period_start, period_end, interval)
    
    return render(request, "finance/reports_equity.html", {
        "workspace": profile.workspace,
        "profile": profile,
        "equity": equity,
        "period_start": period_start,
        "period_end": period_end,
        "interval": interval,
        "cancel_url": _reports_return_url(workspace_id),
    })


# =============================================================================
# Relatório de Investimentos
# =============================================================================

@login_required
def investment_report(request, workspace_id, profile_id):
    """Relatório de posições, aplicações e resgates."""
    profile = require_module(request.user, profile_id, "investments", "view")
    require_module(request.user, profile_id, "overview", "view")
    
    period_start, period_end = _get_period(request)
    
    investments = generate_investment_report(profile, period_start, period_end)
    
    return render(request, "finance/reports_investments.html", {
        "workspace": profile.workspace,
        "profile": profile,
        "investments": investments,
        "period_start": period_start,
        "period_end": period_end,
        "cancel_url": _reports_return_url(workspace_id),
    })


# =============================================================================
# Metas e Reserva
# =============================================================================

@login_required
def goals_report(request, workspace_id, profile_id):
    """Progresso das metas e Reserva."""
    profile = require_module(request.user, profile_id, "investments", "view")
    require_module(request.user, profile_id, "expenses", "view")
    require_module(request.user, profile_id, "overview", "view")
    
    goals = generate_goals_report(profile)
    
    return render(request, "finance/reports_goals.html", {
        "workspace": profile.workspace,
        "profile": profile,
        "goals": goals,
        "cancel_url": _reports_return_url(workspace_id),
    })