# SPDX-License-Identifier: GPL-3.0-only
"""Read-only readiness checks for startup; do NOT create or alter financial data."""
from dataclasses import dataclass
from pathlib import Path
import os

from django.apps import apps
from django.conf import settings
from django.db import connection
from django.template.loader import get_template
from django.urls import resolve, reverse
from django.contrib.staticfiles import finders


@dataclass(frozen=True)
class CheckResult:
    name: str
    detail: str


class StartupValidator:
    """Validation of essential functional dependencies, without mutations.

    This is NOT an integration test suite. It runs once per web startup, after
    Django migrations have been applied by the existing deployment script.
    """

    REQUIRED_URL_NAMES = (
        'home', 'visao-geral', 'despesas', 'investimentos', 'movimentacoes',
        'configuracoes', 'logs', 'relatorios', 'login', 'logout',
        'health-ready', 'configuracoes-api-nova',
    )
    REQUIRED_TEMPLATES = (
        'finance/base.html', 'finance/workspace_page.html',
        'finance/_goal_panel.html', 'finance/_history_chart.html',
        'finance/import_preview.html', 'finance/profile_manage.html',
        'finance/financial_transfer.html', 'finance/reports_dashboard.html',
        'core/settings_dashboard.html', 'core/settings_form.html',
        'core/system_logs_list.html', 'core/user_edit.html',
        'core/error_page.html', 'auth/login.html',
    )
    REQUIRED_STATIC = ('finance/alece.css', 'finance/alece.js',
                       'finance/alece_ui_consistency.css', 'finance/favicon.svg')
    REQUIRED_MODELS = (
        ('finance', 'Workspace'), ('finance', 'WorkspaceMembership'),
        ('finance', 'FinancialProfile'), ('finance', 'ProfileGrant'),
        ('finance', 'BankAccount'), ('finance', 'RecurringExpense'),
        ('finance', 'UnexpectedExpense'), ('finance', 'InvestmentPosition'),
        ('finance', 'ReservePolicy'), ('finance', 'TransactionBatch'),
        ('finance', 'LedgerLeg'), ('finance', 'MonthlyExpense'),
        ('finance', 'MonthlyInvestmentPlan'), ('finance', 'JournalEntry'),
        ('finance', 'ImportBatch'), ('finance', 'ImportRow'),
        ('finance', 'CategorizationRule'), ('finance', 'ReportExport'),
        ('core', 'SystemLog'), ('core', 'UserProfile'),
        ('core', 'RecoveryCode'), ('core', 'AIProviderConfig'),
    )

    def __init__(self):
        self.results = []

    def run(self):
        for name, check in (
            ('rotas', self.routes), ('templates', self.templates),
            ('estaticos', self.statics), ('banco', self.database),
            ('schema', self.schema), ('volumes', self.storage),
        ):
            check()
            self.results.append(CheckResult(name, 'OK'))
        return self.results

    def routes(self):
        for name in self.REQUIRED_URL_NAMES:
            url = reverse(name)
            result = resolve(url)
            if result.url_name != name:
                raise ValueError(f'Rota invertida inconsistente: {name}')

    def templates(self):
        for name in self.REQUIRED_TEMPLATES:
            get_template(name)

    def statics(self):
        for name in self.REQUIRED_STATIC:
            if not finders.find(name):
                raise FileNotFoundError(f'Arquivo estático não encontrado: {name}')

    def database(self):
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            if cursor.fetchone()[0] != 1:
                raise RuntimeError('Banco não retornou o resultado esperado')

    def schema(self):
        present = set(connection.introspection.table_names())
        for app_label, model_name in self.REQUIRED_MODELS:
            table_name = apps.get_model(app_label, model_name)._meta.db_table
            if table_name not in present:
                raise RuntimeError(f'Tabela obrigatória ausente: {app_label}.{model_name}')

    def storage(self):
        # No file creation on startup: preconditions should already be fulfilled.
        paths = [Path(settings.MEDIA_ROOT)]
        if os.environ.get('ALECE_LOG_VALIDACAO', '').lower() in {'1', 'true', 'yes', 'on'}:
            paths.append(Path(settings.BASE_DIR) / 'src' / 'logs')
        for path in paths:
            if not path.is_dir() or not os.access(path, os.W_OK | os.X_OK):
                raise PermissionError(f'Diretório inacessível para escrita: {path}')
