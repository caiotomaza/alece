# SPDX-License-Identifier: GPL-3.0-only
"""Exportação/importação portável APENAS de dados financeiros de um núcleo ALECE.

Formato versionado; remapeia chaves financeiras e não transporta identidade,
permissões, tokens, logs, auditoria, sessões nem metadados de contas de usuários.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import re
import secrets
import zipfile

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from apps.finance import models as finance

SCHEMA_VERSION = 1
FORMAT = 'alece-financeiro'
MODEL_ORDER = (
    'FinancialProfile', 'BankAccount', 'RecurringExpense', 'UnexpectedExpense',
    'InvestmentPosition', 'ReservePolicy', 'MonthlyExpense', 'MonthlyInvestmentPlan',
    'TransactionBatch', 'LedgerLeg', 'JournalEntry', 'ImportBatch', 'ImportRow',
    'CategorizationRule',
)
MODEL_CLASSES = {name: getattr(finance, name) for name in MODEL_ORDER}
# Registros de usuários, concessões (ProfileGrant), logs, tokens, exportações antigas
# e versões de auditoria de regras NÃO podem ser incluídos no backup financeiro.
SKIP_FIELDS = frozenset({'workspace', 'created_by', 'updated_by', 'changed_by',
                         'decided_by', 'idempotency_key'})
USER_REFS = {'created_by', 'updated_by', 'changed_by', 'decided_by'}
MAX_ZIP = 25 * 1024 * 1024
MAX_UNPACKED = 65 * 1024 * 1024
MAX_ROWS = 100_000
FK_RELATIONS = {
    name: {
        f.name: f.related_model.__name__
        for f in model._meta.concrete_fields
        if f.is_relation and f.name not in SKIP_FIELDS
    }
    for name, model in MODEL_CLASSES.items()
}
# Não há permissões, usuários, logs ou segredos na lista.
QUERY_FILTER = {
    'FinancialProfile': 'workspace_id',
    'BankAccount': 'profile__workspace_id',
    'RecurringExpense': 'profile__workspace_id',
    'UnexpectedExpense': 'profile__workspace_id',
    'InvestmentPosition': 'profile__workspace_id',
    'ReservePolicy': 'profile__workspace_id',
    'MonthlyExpense': 'profile__workspace_id',
    'MonthlyInvestmentPlan': 'profile__workspace_id',
    'TransactionBatch': 'profile__workspace_id',
    'LedgerLeg': 'batch__profile__workspace_id',
    'JournalEntry': 'batch__profile__workspace_id',
    'ImportBatch': 'profile__workspace_id',
    'ImportRow': 'batch__profile__workspace_id',
    'CategorizationRule': 'workspace_id',
}


def financial_queryset(name, workspace_id):
    return MODEL_CLASSES[name].objects.filter(**{QUERY_FILTER[name]: workspace_id}).order_by('pk')


def _encoded(v):
    if isinstance(v, (Decimal, date, datetime)):
        return v.isoformat() if not isinstance(v, Decimal) else str(v)
    return v


def _fields(name):
    model = MODEL_CLASSES[name]
    return [f for f in model._meta.concrete_fields
            if not f.primary_key and f.name not in SKIP_FIELDS]


def export_payload(workspace_id):
    tables = {}
    for name in MODEL_ORDER:
        rows = []
        for obj in financial_queryset(name, workspace_id).iterator(chunk_size=1000):
            item = {'id': obj.pk}
            for f in _fields(name):
                value = getattr(obj, f.attname if f.is_relation else f.name)
                item[f.name] = _encoded(value)
            rows.append(item)
        tables[name] = rows
    return {'format': FORMAT, 'version': SCHEMA_VERSION,
            'exported_at': timezone.now().isoformat(), 'tables': tables}


def _to_json(data):
    return json.dumps(data, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def archive_bytes(payload):
    """Contém JSON para restauração e XLSX legível, com checksum de conteúdo."""
    from apps.finance.services.financial_xlsx import render_xlsx
    content = _to_json(payload)
    digest = hashlib.sha256(content).hexdigest()
    spreadsheet = render_xlsx(payload)
    manifest = _to_json({'format': FORMAT, 'version': SCHEMA_VERSION,
                         'financial_json_sha256': digest,
                         'xlsx_sha256': hashlib.sha256(spreadsheet).hexdigest(),
                         'row_counts': {k: len(v) for k, v in payload['tables'].items()}})
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr('financeiro.json', content)
        z.writestr('manifesto.json', manifest)
        z.writestr('leitura_financeira.xlsx', spreadsheet)
        z.writestr('LEIA_ME.txt', (
            'ALECE - EXPORTACAO FINANCEIRA PORTAVEL\n'
            'Importe o ZIP completo, nunca o XLSX isolado.\n'
            'Nao contem contas de usuarios, senhas, permissoes, logs ou tokens.\n'
            'Contem dados financeiros sensiveis: guarde o arquivo em local seguro.\n'
            'O XLSX serve apenas para consulta e NAO pode ser usado para restauracao.\n'
        ).encode('utf-8'))
    return buf.getvalue()


def parse_archive(blob):
    if len(blob) > MAX_ZIP:
        raise ValidationError('Arquivo acima do limite de 25 MiB.')
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            entries = z.infolist()
            expected = {'financeiro.json', 'manifesto.json', 'leitura_financeira.xlsx', 'LEIA_ME.txt'}
            if set(z.namelist()) != expected or len(entries) != len(expected):
                raise ValidationError('Conteúdo inválido: envie um ZIP de exportação ALECE completo.')
            if any(i.is_dir() or i.file_size > MAX_UNPACKED for i in entries) or sum(i.file_size for i in entries) > MAX_UNPACKED:
                raise ValidationError('Arquivo com conteúdo descompactado excessivo.')
            content = z.read('financeiro.json')
            workbook_content = z.read('leitura_financeira.xlsx')
            manifest = json.loads(z.read('manifesto.json'))
    except (zipfile.BadZipFile, UnicodeError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        raise ValidationError('ZIP financeiro inválido ou corrompido.') from exc
    if manifest.get('format') != FORMAT or manifest.get('version') != SCHEMA_VERSION:
        raise ValidationError('Formato ou versão de exportação incompatível.')
    if not secrets.compare_digest(str(manifest.get('financial_json_sha256','')),
                                   hashlib.sha256(content).hexdigest()):
        raise ValidationError('Falha na verificação SHA-256 do arquivo financeiro.')
    if not secrets.compare_digest(str(manifest.get('xlsx_sha256', '')),
                                   hashlib.sha256(workbook_content).hexdigest()):
        raise ValidationError('Falha na verificação SHA-256 da planilha financeira.')
    try:
        payload = json.loads(content)
    except (ValueError, UnicodeError) as exc:
        raise ValidationError('JSON financeiro inválido.') from exc
    validate_payload(payload)
    if manifest.get('row_counts') != {k: len(v) for k,v in payload['tables'].items()}:
        raise ValidationError('Contagens da exportação inconsistentes.')
    return payload


def validate_payload(payload):
    if not isinstance(payload, dict) or payload.get('format') != FORMAT or payload.get('version') != SCHEMA_VERSION:
        raise ValidationError('Arquivo não é um snapshot financeiro compatível.')
    tables = payload.get('tables')
    if not isinstance(tables, dict) or set(tables) != set(MODEL_ORDER):
        raise ValidationError('Tabelas financeiras ausentes ou inesperadas.')
    total = 0
    source_ids = {}
    for name in MODEL_ORDER:
        rows = tables[name]
        if not isinstance(rows, list):
            raise ValidationError(f'Tabela {name} inválida.')
        total += len(rows)
        allowed = {'id'} | {f.name for f in _fields(name)}
        seen = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != allowed:
                raise ValidationError(f'Campos inesperados em {name}.')
            old = row.get('id')
            if not isinstance(old, int) or isinstance(old,bool) or old <= 0 or old in seen:
                raise ValidationError(f'Identificador repetido ou inválido em {name}.')
            seen.add(old)
            for field, rel_name in FK_RELATIONS[name].items():
                foreign_id = row[field]
                if foreign_id is not None and (not isinstance(foreign_id, int) or isinstance(foreign_id,bool) or foreign_id <= 0):
                    raise ValidationError(f'Referência inválida em {name}.{field}.')
        source_ids[name] = seen
    if total > MAX_ROWS:
        raise ValidationError(f'Exportação excede {MAX_ROWS} registros.')
    for name in MODEL_ORDER:
        for row in tables[name]:
            for field, rel_name in FK_RELATIONS[name].items():
                if field == 'reversal_of':
                    rel_name = 'TransactionBatch'
                foreign_id = row[field]
                if foreign_id is not None and foreign_id not in source_ids.get(rel_name, set()):
                    raise ValidationError(f'Referência financeira órfã: {name}.{field}.')
    # Relações entre entidades de perfis diferentes não podem ser reconstituídas.
    by_id = {name: {row['id']: row for row in tables[name]} for name in MODEL_ORDER}
    def profile_of(model, object_id):
        return by_id[model][object_id]['profile']
    for row in tables['LedgerLeg']:
        if profile_of('TransactionBatch', row['batch']) != profile_of('BankAccount', row['account']):
            raise ValidationError('Lançamento contábil ligado a conta de outro perfil.')
    for row in tables['JournalEntry']:
        if row['bank_account'] is not None and profile_of('TransactionBatch', row['batch']) != profile_of('BankAccount', row['bank_account']):
            raise ValidationError('Partida contábil ligada a conta de outro perfil.')
    for row in tables['TransactionBatch']:
        for key, related in (('recurring_expense','RecurringExpense'), ('monthly_expense','MonthlyExpense'),
                             ('monthly_investment_plan','MonthlyInvestmentPlan'), ('unexpected_expense','UnexpectedExpense'),
                             ('investment','InvestmentPosition')):
            if row[key] is not None and row['profile'] != profile_of(related, row[key]):
                raise ValidationError(f'Vínculo de movimentação entre perfis diferentes: {key}.')
        if row['reversal_of'] is not None and row['profile'] != profile_of('TransactionBatch', row['reversal_of']):
            raise ValidationError('Estorno de movimentação em outro perfil.')
    for name, relation in (('MonthlyExpense','RecurringExpense'), ('MonthlyInvestmentPlan','InvestmentPosition')):
        field = 'recurring_expense' if name == 'MonthlyExpense' else 'investment'
        for row in tables[name]:
            if row['profile'] != profile_of(relation, row[field]):
                raise ValidationError(f'Planejamento mensal vinculado a outro perfil: {name}.')
    for row in tables['ImportBatch']:
        if row['account'] is not None and row['profile'] != profile_of('BankAccount', row['account']):
            raise ValidationError('Lote de importação vinculado a conta de outro perfil.')
    for row in tables['ImportRow']:
        if row['linked_batch'] is not None and profile_of('ImportBatch', row['batch']) != profile_of('TransactionBatch', row['linked_batch']):
            raise ValidationError('Linha importada ligada a movimentação de outro perfil.')
    return total


def _available_name(raw, used, maxlen):
    base = (raw or '').strip()
    if not base:
        raise ValidationError('Nome vazio em perfil ou regra financeira.')
    if base not in used:
        used.add(base)
        return base
    for index in range(1, 100001):
        suffix = f' (Importado {index})'
        value = base[:maxlen-len(suffix)] + suffix
        if value not in used:
            used.add(value)
            return value
    raise ValidationError('Excesso de nomes coincidentes.')


def _remap_suggested_link(value, mapping):
    """Mapeia referências conhecidas da categorização; rejeita as desconhecidas."""
    if not isinstance(value, dict):
        return value
    mapping_keys = {
        'recurring_expense_id':'RecurringExpense', 'investment_id':'InvestmentPosition',
        'account_id':'BankAccount', 'unexpected_expense_id':'UnexpectedExpense',
        'transaction_batch_id':'TransactionBatch',
    }
    out = {}
    for key, item in value.items():
        if key in mapping_keys and isinstance(item, int):
            try: out[key] = mapping[mapping_keys[key]][item]
            except KeyError: raise ValidationError(f'Referência inválida em campo de sugestão: {key}')
        else:
            out[key] = item
    return out


def import_payload(payload, *, workspace, actor, grant_all_members=True):
    """Importação aditiva e atômica, novos IDs. Nunca sobrescreve perfis existentes.

    Autorização deve ser verificada pela view ANTES de entrar. Serialização via
    lock do workspace evita colisões e respeita limite de cinco perfis ativos.
    """
    validate_payload(payload)
    from apps.finance.models import ProfileGrant, Workspace, WorkspaceMembership
    mapping = defaultdict(dict)
    counters = {}
    deferred_reversals = []
    with transaction.atomic():
        Workspace.objects.select_for_update().get(pk=workspace.pk)
        existing_names = set(finance.FinancialProfile.objects.filter(workspace=workspace).values_list('name',flat=True))
        rule_names = set(finance.CategorizationRule.objects.filter(workspace=workspace).values_list('name',flat=True))
        active_count = finance.FinancialProfile.objects.filter(workspace=workspace, is_archived=False, deleted_at__isnull=True).count()
        for name in MODEL_ORDER:
            model = MODEL_CLASSES[name]
            for row in payload['tables'][name]:
                kwargs = {}
                delayed_ts = {}
                for f in _fields(name):
                    value = row[f.name]
                    if f.name == 'reversal_of':
                        if value is not None:
                            deferred_reversals.append((row['id'], value))
                        continue
                    if f.is_relation:
                        if value is not None:
                            reference_name = FK_RELATIONS[name][f.name]
                            try: value = mapping[reference_name][value]
                            except KeyError: raise ValidationError(f'Falha ao remapear {name}.{f.name}')
                        kwargs[f.attname] = value
                    elif getattr(f, 'auto_now', False) or getattr(f, 'auto_now_add', False):
                        if value is not None: delayed_ts[f.name] = f.to_python(value)
                    else:
                        if isinstance(f, (models.DateField, models.DateTimeField, models.DecimalField)) and value is not None:
                            value = f.to_python(value)
                        if f.name == 'suggested_link':
                            value = _remap_suggested_link(value, mapping)
                        kwargs[f.name] = value
                if name == 'FinancialProfile':
                    kwargs['workspace'] = workspace
                    kwargs['name'] = _available_name(kwargs['name'], existing_names, 80)
                    # Campos de exclusão lógica são preservados. Limite de perfis ativos.
                    if not kwargs.get('is_archived') and kwargs.get('deleted_at') is None:
                        if active_count >= 5:
                            kwargs['is_archived'] = True
                        else:
                            active_count += 1
                if name == 'CategorizationRule':
                    kwargs['workspace'] = workspace
                    kwargs['name'] = _available_name(kwargs['name'], rule_names, 120)
                    kwargs['created_by'] = actor
                    kwargs['updated_by'] = None
                if name == 'ImportBatch':
                    kwargs['created_by'] = actor
                if name == 'ImportRow':
                    kwargs['decided_by'] = None
                if name == 'TransactionBatch':
                    kwargs['created_by'] = None
                # Reaproveitar idempotency_key do banco antigo pode colidir.
                if any(f.name == 'idempotency_key' for f in model._meta.fields):
                    kwargs['idempotency_key'] = None
                obj = model(**kwargs)
                obj.full_clean()
                obj.save(force_insert=True)
                if delayed_ts:
                    model.objects.filter(pk=obj.pk).update(**delayed_ts)
                mapping[name][row['id']] = obj.pk
            counters[name] = len(payload['tables'][name])
        for old_batch, old_reversal in deferred_reversals:
            finance.TransactionBatch.objects.filter(pk=mapping['TransactionBatch'][old_batch]).update(
                reversal_of_id=mapping['TransactionBatch'][old_reversal]
            )
        if grant_all_members:
            users = WorkspaceMembership.objects.filter(workspace=workspace)
            for member in users:
                for target_pk in mapping['FinancialProfile'].values():
                    target = finance.FinancialProfile.objects.get(pk=target_pk)
                    if target.deleted_at is not None:
                        continue
                    ProfileGrant.objects.create(
                        membership=member, profile_id=target_pk, can_view=True, can_edit=True,
                        overview_level='edit', accounts_level='edit', expenses_level='edit',
                        investments_level='edit', movements_level='edit'
                    )
    return counters
