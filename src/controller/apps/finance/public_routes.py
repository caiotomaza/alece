# SPDX-License-Identifier: GPL-3.0-only
"""URLs públicas estáveis sem IDs; seleção do núcleo permanece autorizada no servidor."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_GET
from django.core.exceptions import PermissionDenied

from apps.core.permissions import get_user_workspace_memberships, user_has_workspace_access
from apps.finance import views

NAV_SECTIONS = {
    "overview": "visao-geral",
    "expenses": "despesas",
    "investments": "investimentos",
    "movements": "movimentacoes",
    "settings": "configuracoes",
}


def active_workspace_id(request):
    """Never trust a client-provided workspace ID without a current membership."""
    memberships = get_user_workspace_memberships(request.user).order_by('workspace_id')
    selected = request.session.get('alece_workspace_id')
    if selected is not None and memberships.filter(workspace_id=selected).exists():
        return selected
    ids = list(memberships.values_list('workspace_id', flat=True)[:2])
    if len(ids) == 1:
        request.session['alece_workspace_id'] = ids[0]
        return ids[0]
    return None


@login_required
@require_GET
def select_workspace(request, workspace_id):
    if not user_has_workspace_access(request.user, workspace_id):
        raise PermissionDenied('Núcleo não autorizado.')
    request.session['alece_workspace_id'] = workspace_id
    return redirect('visao-geral')


@login_required
@require_GET
def public_page(request, section='overview'):
    workspace_id = active_workspace_id(request)
    if workspace_id is None:
        return redirect('home')
    if section == 'settings':
        from apps.core.settings_views import settings_dashboard
        return settings_dashboard(request, workspace_id)
    return views.workspace_page(request, workspace_id, section=section)


@login_required
@require_GET
def public_technical_reports(request):
    from apps.finance.financial_transfer_views import technical_reports
    workspace_id = active_workspace_id(request)
    if workspace_id is None:
        return redirect('home')
    return technical_reports(request, workspace_id)


@login_required
@require_GET
def public_financial_export(request):
    from apps.finance.financial_transfer_views import export_financial
    workspace_id = active_workspace_id(request)
    if workspace_id is None:
        return redirect('home')
    return export_financial(request, workspace_id)


@login_required
def public_financial_import(request):
    from apps.finance.financial_transfer_views import import_financial
    if request.method != 'POST':
        from django.http import HttpResponseNotAllowed
        return HttpResponseNotAllowed(['POST'])
    workspace_id = active_workspace_id(request)
    if workspace_id is None:
        return redirect('home')
    return import_financial(request, workspace_id)
