# SPDX-License-Identifier: GPL-3.0-only
"""Painel técnico + exportação/importação financeira estritamente administrativa."""
from __future__ import annotations

from pathlib import Path
import hashlib
import io
import os
import secrets
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Sum
from django.http import FileResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.core.permissions import require_workspace_admin, get_accessible_profiles
from apps.core.models import SystemLog
from apps.finance.models import (FinancialProfile, BankAccount, InvestmentPosition,
                                 TransactionBatch, ImportBatch, WorkspaceMembership)
from apps.finance.services.financial_transfer import (
    export_payload, archive_bytes, parse_archive, import_payload, MODEL_ORDER,
)


def _admin(request, workspace_id):
    try:
        require_workspace_admin(request.user, workspace_id)
    except PermissionError as exc:
        raise PermissionDenied('Esta operação exige administrador do espaço financeiro.') from exc
    from apps.finance.models import Workspace
    return Workspace.objects.get(pk=workspace_id)


def _overview(workspace):
    profiles = FinancialProfile.objects.filter(workspace=workspace, deleted_at__isnull=True)
    current = profiles.filter(is_archived=False)
    return {
        'profiles_count': profiles.count(),
        'active_count': current.count(),
        'accounts_count': BankAccount.objects.filter(profile__workspace=workspace).count(),
        'movements_count': TransactionBatch.objects.filter(profile__workspace=workspace).count(),
        'import_batches_count': ImportBatch.objects.filter(profile__workspace=workspace).count(),
        'investments_value': InvestmentPosition.objects.filter(profile__workspace=workspace).aggregate(
            total=Sum('current_value'))['total'] or 0,
        'account_balance': BankAccount.objects.filter(profile__workspace=workspace, is_archived=False).aggregate(
            total=Sum('balance'))['total'] or 0,
        'unknown_accounts': BankAccount.objects.filter(profile__workspace=workspace, balance__isnull=True).count(),
        'profile_rows': [
            {'name': p.name, 'archived': p.is_archived, 'deleted': p.deleted_at is not None}
            for p in FinancialProfile.objects.filter(workspace=workspace).order_by('name')
        ],
        'entity_types': len(MODEL_ORDER),
    }


@login_required
@require_GET
def technical_reports(request, workspace_id):
    workspace = _admin(request, workspace_id)
    return render(request, 'finance/financial_transfer.html', {
        'workspace': workspace, 'nav_profiles': list(get_accessible_profiles(request.user).filter(workspace=workspace)),
        'active_nav': 'settings', 'overview': _overview(workspace),
        'import_max_mib': 25,
    })


@login_required
@require_GET
def export_financial(request, workspace_id):
    workspace = _admin(request, workspace_id)
    payload = export_payload(workspace.pk)
    content = archive_bytes(payload)
    SystemLog.objects.create(
        severity='info', module='imports', action='view', result='success',
        user=request.user, workspace=workspace,
        description='Exportação financeira portável solicitada',
        details={'total_registros': sum(len(rows) for rows in payload['tables'].values())},
    )
    response = FileResponse(io.BytesIO(content), as_attachment=True,
                            filename=f'alece_financeiro_{date.today().isoformat()}.zip',
                            content_type='application/zip')
    response['Cache-Control'] = 'no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


def _destination_backup(workspace):
    """Backup financeiro local validado com SHA-256 antes de QUALQUER modificação."""
    home = Path.home()
    target = home / 'backups'
    target.mkdir(mode=0o700, parents=True, exist_ok=True)
    timestamp = timezone.now().strftime('%Y-%m-%d_%H-%M-%S')
    # Extra entropia para duas intervenções no mesmo segundo.
    base = target / f'{timestamp}__alece-financeiro-antes-importacao-{secrets.token_hex(3)}.zip'
    data = archive_bytes(export_payload(workspace.pk))
    with base.open('xb') as f:
        os.fchmod(f.fileno(), 0o600)
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    hexdigest = hashlib.sha256(data).hexdigest()
    sha_path = Path(str(base) + '.sha256')
    with sha_path.open('x',encoding='utf-8') as f:
        os.fchmod(f.fileno(), 0o600)
        f.write(f'{hexdigest}  {base.name}\n')
    if hashlib.sha256(base.read_bytes()).hexdigest() != hexdigest:
        raise ValidationError('Falha na verificação de backup do destino.')
    return base


@login_required
@require_POST
def import_financial(request, workspace_id):
    workspace = _admin(request, workspace_id)
    uploaded = request.FILES.get('archive')
    if not uploaded or uploaded.size > 25*1024*1024 or uploaded.size == 0:
        messages.error(request, 'Selecione um arquivo ZIP financeiro ALECE de até 25 MiB.')
        return redirect('finance:technical-reports', workspace_id=workspace_id)
    if request.POST.get('confirm') != 'IMPORTAR' or request.POST.get('grant_all') != 'yes':
        messages.error(request, 'Confirme a importação e a concessão inicial de acesso aos usuários atuais.')
        return redirect('finance:technical-reports', workspace_id=workspace_id)
    try:
        payload = parse_archive(uploaded.read())
        backup = _destination_backup(workspace)
        counts = import_payload(payload, workspace=workspace, actor=request.user, grant_all_members=True)
    except (ValidationError, OSError, ValueError) as error:
        # OSError/ValueError podem incluir caminhos locais e trechos de dados enviados.
        # Uma mensagem pública não pode retransmitir esses detalhes.
        if isinstance(error, ValidationError):
            message = '; '.join(error.messages)
        else:
            message = 'O arquivo não pôde ser processado. Verifique o formato e tente novamente.'
        messages.error(request, f'Importação cancelada: {message}')
        return redirect('finance:technical-reports', workspace_id=workspace_id)
    # O evento registra apenas contagens, jamais credenciais ou conteúdo financeiro.
    SystemLog.objects.create(
        severity='info', module='imports', action='import', result='success',
        user=request.user, workspace=workspace,
        description='Restauração financeira portável concluída',
        details={'total_registros': sum(counts.values()), 'perfis': counts['FinancialProfile']},
    )
    messages.success(request, f'Importação concluída: {counts["FinancialProfile"]} perfis, '
                     f'{counts["TransactionBatch"]} movimentações. Os usuários atuais receberam acesso de edição '
                     'aos perfis importados; revise as permissões em Configurações.')
    return redirect('finance:technical-reports', workspace_id=workspace_id)
