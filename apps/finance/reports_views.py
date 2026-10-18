# SPDX-License-Identifier: GPL-3.0-only
"""Views para relatórios financeiros consolidados."""
import dataclasses
import hashlib
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from apps.core.permissions import require_module, user_can_module
from apps.finance.models import ReportExport
from apps.finance.services.reports import (
    generate_dashboard_report, generate_dre_report, generate_equity_evolution_report,
    generate_investment_report, generate_goals_report,
    export_dre_csv, export_equity_csv, export_investment_json, export_goals_json,
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


# =============================================================================
# Exportação de Relatórios
# =============================================================================

@login_required
def export_report(request, workspace_id, profile_id, report_type):
    """Exporta relatório em CSV ou JSON."""
    profile = require_module(request.user, profile_id, "overview", "view")
    require_module(request.user, profile_id, "expenses", "view")
    require_module(request.user, profile_id, "investments", "view")
    
    period_start = date.fromisoformat(request.GET.get("period_start"))
    period_end = date.fromisoformat(request.GET.get("period_end"))
    fmt = request.GET.get("format", "csv")  # csv | json
    
    # Gerar relatório
    if report_type == "dre":
        report = generate_dre_report(profile, period_start, period_end)
        if fmt == "csv":
            content = export_dre_csv(report)
            filename = f"dre_{profile.name}_{period_start}_{period_end}.csv"
        else:
            import json
            class DecimalEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, Decimal):
                        return str(obj)
                    return super().default(obj)
            content = json.dumps(dataclasses.asdict(report), cls=DecimalEncoder, ensure_ascii=False).encode("utf-8")
            filename = f"dre_{profile.name}_{period_start}_{period_end}.json"
    elif report_type == "equity":
        report = generate_equity_evolution_report(profile, period_start, period_end)
        if fmt == "csv":
            content = export_equity_csv(report)
            filename = f"equity_{profile.name}_{period_start}_{period_end}.csv"
        else:
            import json
            class DecimalEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, Decimal):
                        return str(obj)
                    return super().default(obj)
            content = json.dumps(dataclasses.asdict(report), cls=DecimalEncoder, ensure_ascii=False).encode("utf-8")
            filename = f"equity_{profile.name}_{period_start}_{period_end}.json"
    elif report_type == "investments":
        report = generate_investment_report(profile, period_start, period_end)
        if fmt == "csv":
            content = export_investment_json(report)
            filename = f"investments_{profile.name}_{period_start}_{period_end}.csv"
        else:
            import json
            class DecimalEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, Decimal):
                        return str(obj)
                    return super().default(obj)
            content = json.dumps(dataclasses.asdict(report), cls=DecimalEncoder, ensure_ascii=False).encode("utf-8")
            filename = f"investments_{profile.name}_{period_start}_{period_end}.json"
    elif report_type == "goals":
        report = generate_goals_report(profile)
        if fmt == "csv":
            content = export_goals_json(report)
            filename = f"goals_{profile.name}_{period_start}_{period_end}.csv"
        else:
            import json
            class DecimalEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, Decimal):
                        return str(obj)
                    return super().default(obj)
            content = json.dumps(dataclasses.asdict(report), cls=DecimalEncoder, ensure_ascii=False).encode("utf-8")
            filename = f"goals_{profile.name}_{period_start}_{period_end}.json"
    else:
        raise Http404("Tipo de relatório não suportado.")
    
    # Salvar export para auditoria
    export = ReportExport.objects.create(
        profile=profile, report_type=report_type, format=fmt.upper(),
        period_start=period_start, period_end=period_end,
        requested_by=request.user, status=ReportExport.Status.GENERATING
    )
    export.file.save(filename, ContentFile(content))
    export.status = ReportExport.Status.READY
    export.completed_at = timezone.now()
    export.file_hash = hashlib.sha256(content).hexdigest()
    export.save()
    
    response = HttpResponse(content, content_type="text/csv; charset=utf-8" if fmt == "csv" else "application/json")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response