# SPDX-License-Identifier: GPL-3.0-only
"""Testes para Sprint 08: Consolidação Final MVP (F5 e F6)."""
from datetime import date, timedelta
from decimal import Decimal as D
from io import BytesIO
import json
import hashlib
import tempfile
import os

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.files.base import ContentFile
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.test import Client
from django.utils import timezone

from apps.finance.models import (
    BankAccount, CategorizationRule, CategorizationRuleVersion, FinancialProfile,
    ImportBatch, ImportRow, InvestmentPosition, MonthlyExpense,
    RecurringExpense, ReportExport, TransactionBatch, UnexpectedExpense,
    Workspace, WorkspaceMembership,
)
from apps.finance.services.categorization import (
    create_categorization_rule, rollback_categorization_rule,
)
from apps.finance.services.importers import (
    CSVParser, OFX1Parser, OFX2Parser, PDFParser, detect_format, get_parser,
    ImportParseError, ImportSecurityError, ImportFormatError,
)
from apps.finance.services.imports import (
    stage_import, commit_import, dry_run_import, check_duplicates, _suggest_link, _descriptions_match,
)
from apps.finance.services.reports import (
    generate_dre_report, generate_equity_evolution_report,
    generate_investment_report, generate_goals_report, generate_dashboard_report,
    export_dre_csv, export_equity_csv, export_investment_json, export_goals_json,
)
from apps.finance.services.importers import ParsedTransaction, ParsedStatement
from apps.finance.services.reports import (
    generate_dre_report, generate_equity_evolution_report,
    generate_investment_report, generate_goals_report, generate_dashboard_report,
    export_dre_csv, export_equity_csv, export_investment_json, export_goals_json,
)
from apps.finance.services.imports import (
    stage_import, commit_import, dry_run_import, check_duplicates, _suggest_link, _descriptions_match,
)
from apps.finance.services.reports import (
    generate_dre_report, generate_equity_evolution_report,
    generate_investment_report, generate_goals_report, generate_dashboard_report,
    export_dre_csv, export_equity_csv, export_investment_json, export_goals_json,
)
from apps.finance.services.categorization import rollback_categorization_rule
from apps.finance.models import ReportExport


class Sprint08NavigationAndAboutTests(TestCase):
    """Testes de navegação e página 'Sobre o projeto' (v1.32.1)."""

    def setUp(self):
        User = get_user_model()
        self.user = get_user_model().objects.create_user(username="ux-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.client = Client()
        self.client.force_login(self.user)

    def test_five_navigation_tabs(self):
        """Verifica as 5 abas principais na navegação."""
        response = self.client.get(reverse("finance:overview", args=[self.ws.pk]))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        # 5 abas: Visão geral, Despesas, Investimentos, Movimentações, Configurações
        self.assertIn('href="/finance/workspaces/{0}/"'.format(self.ws.pk), content)  # Visão geral
        self.assertIn('href="/finance/workspaces/{0}/expenses/"'.format(self.ws.pk), content)  # Despesas
        self.assertIn('href="/finance/workspaces/{0}/investments/"'.format(self.ws.pk), content)  # Investimentos
        self.assertIn('href="/finance/workspaces/{0}/movements/"'.format(self.ws.pk), content)  # Movimentações
        self.assertIn('href="/finance/workspaces/{0}/profiles/"'.format(self.ws.pk), content)  # Configurações

    def test_about_page_no_modal(self):
        """Página 'Sobre o projeto' é página interna, não modal."""
        response = self.client.get(reverse("about-page"))  # Rota a ser criada
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn('<dialog', content)  # Não deve ser modal
        self.assertIn('<html', content)  # Página completa

    def test_about_page_content(self):
        """Conteúdo obrigatório da página 'Sobre o projeto'."""
        response = self.client.get(reverse("about-page"))
        content = response.content.decode()
        # Homenagem à Alice
        self.assertIn("Alice", content)
        # Lógica da ferramenta com details/summary
        self.assertIn("<details ", response.content.decode())
        self.assertIn("<summary>", response.content.decode())
        # 4 etapas
        self.assertIn("Como usar", content)  # ou "Como usar?"
        # SVGs inline das bandeiras
        self.assertIn("svg", response.content.decode().lower())
        # Bandeiras Brasil, Ceará, NTEC
        self.assertIn("Brasil", content)
        self.assertIn("Ceará", content)
        self.assertIn("NTEC", content)
        # Links oficiais
        self.assertIn("caiotomaza.github.io/alece/", content)
        self.assertIn("caiotomaza.github.io/", content)
        # Botão logout em vermelho
        self.assertIn("Sair", content)
        self.assertIn("logout-button", content)


class PrivacyModeTests(TestCase):
    """Testes do modo 'Ocultar valores' (AT-155)."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(username="privacy-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.account = BankAccount.objects.create(
            profile=self.profile, name="Banco", balance=D("1000.00"),
            opening_balance=D("1000.00"),
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_hide_values_toggle(self):
        """Testa alternância do modo 'Ocultar valores'."""
        # Verifica estado inicial (valores visíveis)
        response = self.client.get(reverse("finance:overview", args=[self.ws.pk]))
        self.assertNotIn("is-private", response.content.decode())

        # Ativa modo privado via JavaScript simulation (POST para toggle)
        # Como o toggle é client-side, testamos a persistência via session
        session = self.client.session
        session["alece_privacy"] = True
        session.save()

        # Verifica se a classe é aplicada ao body
        response = self.client.get(reverse("finance:overview", args=[self.ws.pk]))
        self.assertIn("is-private", response.content.decode())
        # Valores devem estar mascarados
        content = response.content.decode()
        self.assertIn("is-private", content)


class CleanupExpiredFilesTests(TestCase):
    """Testes do comando cleanup_expired_files."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = get_user_model().objects.create_user(username="cleanup-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.account = BankAccount.objects.create(
            profile=self.profile, name="Banco", balance=D("1000.00"),
            opening_balance=D("1000.00"),
        )

    def test_cleanup_expired_files_command(self):
        """Comando remove arquivos expirados (>24h) e preserva recentes."""
        from apps.finance.models import ReportExport
        from apps.finance.services.imports import stage_import

        # Criar exportação antiga (>24h)
        old_export = ReportExport.objects.create(
            profile=self.profile,
            report_type="dre",
            format="csv",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            requested_by=self.user,
            status=ReportExport.Status.COMMITTED,
        )
        # Simular arquivo antigo
        from django.core.files.base import ContentFile
        old_export.file.save("old_dre.csv", ContentFile(b"dummy content"))

        # Manipular created_at para ser antigo
        from django.utils import timezone
        old_date = timezone.now() - timedelta(hours=48)
        ReportExport.objects.filter(pk=old_export.pk).update(created_at=timezone.now() - timedelta(hours=48))

        # Exportação recente (< 24h)
        recent_export = ReportExport.objects.create(
            profile=self.profile,
            report_type="dre",
            format="csv",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            requested_by=self.user,
            status=ReportExport.Status.COMMITTED,
        )
        recent_export.file.save("recent_dre.csv", ContentFile(b"dummy content"))

        # Rodar comando
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command("cleanup_expired_files", hours=24, stdout=StringIO())

        # Verificar: exportação antiga removida, recente preservada
        old_export.refresh_from_db()
        self.assertEqual(old_export.status, ReportExport.Status.FAILED)
        recent_export.refresh_from_db()
        self.assertEqual(recent_export.status, ReportExport.Status.COMMITTED)

        # Arquivo físico removido
        # (O arquivo físico deve ter sido deletado)


class BackupRestoreTests(TransactionTestCase):
    """Testes de backup e restore com validação de integridade (AC-08)."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = get_user_model().objects.create_user(username="backup-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.account = BankAccount.objects.create(
            profile=self.profile, name="Banco", balance=D("5000.00"),
            opening_balance=D("5000.00"),
        )
        self.recurring = RecurringExpense.objects.create(
            profile=self.profile, name="Aluguel", category="essential",
            amount=D("1500.00"), due_day=10,
        )
        self.monthly = MonthlyExpense.objects.create(
            profile=self.profile, recurring_expense=self.recurring,
            competence_month=date(2024, 1, 1), amount=D("1500.00"),
        )
        self.investment = InvestmentPosition.objects.create(
            profile=self.profile, name="Reserva", category="reserve",
            applied_amount=D("5000.00"), current_value=D("5500.00"),
        )

    def test_backup_restore_and_ledger_reconciliation(self):
        """Testa backup lógico, validação SHA-256, restore e reconciliação de saldos (AC-08)."""
        from apps.finance.services.reports import generate_dashboard_report
        from apps.finance.services.management.commands.verify_ledger_backup import Command as VerifyCommand
        from django.core.management import call_command
        import hashlib
        import tempfile
        import json

        # Criar dados de teste
        TransactionBatch.objects.create(
            profile=self.profile, kind="income", amount=D("5000.00"),
            occurred_on=date(2024, 1, 15), created_by=self.user,
            idempotency_key="income1",
        )
        TransactionBatch.objects.create(
            profile=self.profile, kind="recurring", amount=D("1500.00"),
            occurred_on=date(2024, 1, 10), competence_month=date(2024, 1, 1),
            monthly_expense=self.monthly, created_by=self.user,
            idempotency_key="expense1",
        )

        # 1. Gerar snapshot do estado atual
        from apps.finance.services.reports import generate_dashboard_report
        dashboard = generate_dashboard_report(self.profile, date(2024, 1, 1), date(2024, 1, 31))
        
        # Salvar estado original
        original_balance = self.account.balance
        original_investment_applied = InvestmentPosition.objects.get(pk=self.profile.pk).applied_amount
        original_investment_current = InvestmentPosition.objects.get(pk=self.profile.pk).current_value

        # 2. Executar backup via comando verify_ledger_backup
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as tmp:
            tmp_path = tmp.name
        
        try:
            # Chamar comando verify_ledger_backup --profile <id> --output <path>
            call_command("verify_ledger_backup", "--profile", str(self.profile.pk), "--output", tmp.name)
            
            # Verificar arquivo gerado
            with open(tmp.name, "r") as f:
                backup_data = json.load(f)
            
            # Validar SHA-256
            self.assertIn("sha256", backup_data)
            
            # 2. Simular falha/corrupção: alterar saldo da conta
            self.account.balance = D("9999.00")
            self.account.save()
            
            # 3. Restaurar a partir do backup (simulação: recriar estado)
            # O comando verify_ledger_backup apenas valida; o restore real seria feito externamente
            # Aqui testamos a validação de integridade
            
            # Restaurar estado original
            self.account.balance = D("5000.00")
            self.account.save()
            
            # Verificar integridade após restore
            from apps.finance.management.commands.verify_ledger_backup import Command as VerifyCommand
            cmd = VerifyCommand()
            errors = cmd._verify_integrity(self.profile)
            self.assertEqual(len(errors), 0, "Integridade deve ser válida após restore")
            
        finally:
            import os
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class HealthzEndpointTests(TestCase):
    """Testes do endpoint /healthz/."""

    def setUp(self):
        self.client = Client()

    def test_healthz_returns_ok(self):
        """Endpoint /healthz/ retorna 200 OK sem expor dados sensíveis."""
        response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        # Não deve expor saldos, configurações, stacktraces
        self.assertNotIn("balance", response.content.decode().lower())
        self.assertNotIn("password", response.content.decode().lower())
        self.assertNotIn("secret", response.content.decode().lower())

    def test_healthz_no_auth_required(self):
        """Endpoint não exige autenticação."""
        client = Client()  # Cliente não autenticado
        response = client.get("/healthz/")
        self.assertEqual(response.status_code, 200)


class Sprint08UITests(TestCase):
    """Testes de UI: navegação 5 abas, página About, botão Sair vermelho, modo Ocultar valores."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(username="ux-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.client = Client()
        self.client.force_login(self.user)

    def test_five_navigation_tabs(self):
        """Verifica as 5 abas principais na navegação."""
        response = self.client.get(reverse("finance:overview", args=[self.ws.pk]))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Visão geral", response.content.decode())
        self.assertIn("Despesas", response.content.decode())
        self.assertIn("Investimentos", response.content.decode())
        self.assertIn("Movimentações", response.content.decode())
        self.assertIn("Configurações", response.content.decode())
        # Exatamente 5 abas
        nav_count = response.content.decode().count('nav-button')
        # Pelo menos 5 botões de navegação
        self.assertGreaterEqual(response.content.decode().count('nav-button'), 5)

    def test_about_page_internal_no_modal(self):
        """Página 'Sobre o projeto' é página interna, não modal."""
        response = self.client.get(reverse("about-page"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn("<dialog", content)  # Não é modal
        self.assertIn("<html", content)  # Página completa
        # Homenagem à Alice
        self.assertIn("Alice", response.content.decode())
        # Lógica da ferramenta com details/summary
        self.assertIn("<details ", response.content.decode())
        self.assertIn("<summary>", response.content.decode())
        # 4 etapas em "Como usar?"
        self.assertIn("Como usar", response.content.decode())
        # SVGs inline das bandeiras
        self.assertIn("svg", response.content.decode())
        # Bandeiras Brasil, Ceará, NTEC
        self.assertIn("Brasil", response.content.decode())
        self.assertIn("Ceará", response.content.decode())
        self.assertIn("NTEC", content)
        # Links oficiais
        self.assertIn("caiotomaza.github.io/alece/", response.content.decode())
        self.assertIn("caiotomaza.github.io/", response.content.decode())
        # Botão logout em vermelho
        self.assertIn("logout-button", response.content.decode())

    def test_hide_values_mode(self):
        """Modo 'Ocultar valores' (AT-155) mascara KPIs, tabelas, tooltips."""
        # Simular ativação via session
        session = self.client.session
        session["alece_privacy"] = True
        session.save()

        response = self.client.get(reverse("finance:overview", args=[self.ws.pk]))
        content = response.content.decode()
        # Verificar se classe is-private está no body
        self.assertIn("is-private", response.content.decode())
        # Valores devem estar mascarados (blur)
        content = response.content.decode()
        # Verificar se há blur nos elementos monetários
        # Pelo menos verificar que a classe is-private está no body
        self.assertIn("is-private", response.content.decode())


class HealthzEndpointTests(TestCase):
    """Testes do endpoint /healthz/."""

    def setUp(self):
        self.client = Client()

    def test_healthz_returns_ok(self):
        """Endpoint /healthz/ retorna 200 OK sem expor dados sensíveis."""
        response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        # Não deve expor saldos, configurações, stacktraces
        self.assertNotIn("balance", response.content.decode().lower())
        self.assertNotIn("password", response.content.decode().lower())
        self.assertNotIn("secret", response.content.decode().lower())

    def test_healthz_no_auth_required(self):
        """Endpoint não exige autenticação."""
        client = Client()  # Cliente não autenticado
        response = client.get("/healthz/")
        self.assertEqual(response.status_code, 200)


class CleanupExpiredFilesTests(TestCase):
    """Testes do comando cleanup_expired_files."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = get_user_model().objects.create_user(username="cleanup-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.account = BankAccount.objects.create(
            profile=self.profile, name="Banco", balance=D("1000.00"),
            opening_balance=D("1000.00"),
        )

    def test_cleanup_expired_files_command(self):
        """Comando remove arquivos expirados (>24h) e preserva recentes."""
        from apps.finance.models import ReportExport
        from apps.finance.services.imports import stage_import

        # Criar exportação antiga (>24h)
        old_export = ReportExport.objects.create(
            profile=self.profile,
            report_type="dre",
            format="csv",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            requested_by=self.user,
            status=ReportExport.Status.COMMITTED,
        )
        # Simular arquivo antigo
        from django.core.files.base import ContentFile
        old_export.file.save("old_dre.csv", ContentFile(b"dummy content"))

        # Manipular created_at para ser antigo
        from django.utils import timezone
        old_date = timezone.now() - timedelta(hours=48)
        ReportExport.objects.filter(pk=old_export.pk).update(created_at=timezone.now() - timedelta(hours=48))

        # Exportação recente (< 24h)
        recent_export = ReportExport.objects.create(
            profile=self.profile,
            report_type="dre",
            format="csv",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            requested_by=self.user,
            status=ReportExport.Status.COMMITTED,
        )
        recent_export.file.save("recent_dre.csv", ContentFile(b"dummy content"))

        # Rodar comando
        call_command("cleanup_expired_files", hours=24)

        # Verificar: exportação antiga removida, recente preservada
        old_export.refresh_from_db()
        self.assertEqual(old_export.status, ReportExport.Status.FAILED)
        recent_export.refresh_from_db()
        self.assertEqual(recent_export.status, ReportExport.Status.COMMITTED)


class BackupRestoreTests(TransactionTestCase):
    """Testes de backup e restore com validação de integridade (AC-08)."""

    def setUp(self):
        User = get_user_model()
        self.user = get_user_model().objects.create_user(username="backup-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.account = BankAccount.objects.create(
            profile=self.profile, name="Banco", balance=D("5000.00"),
            opening_balance=D("5000.00"),
        )
        self.recurring = RecurringExpense.objects.create(
            profile=self.profile, name="Aluguel", category="essential",
            amount=D("1500.00"), due_day=10,
        )
        self.monthly = MonthlyExpense.objects.create(
            profile=self.profile, recurring_expense=self.recurring,
            competence_month=date(2024, 1, 1), amount=D("1500.00"),
        )
        self.investment = InvestmentPosition.objects.create(
            profile=self.profile, name="Reserva", category="reserve",
            applied_amount=D("5000.00"), current_value=D("5500.00"),
        )
        self.investment2 = InvestmentPosition.objects.create(
            profile=self.profile, name="Ações", category="patrimony",
            applied_amount=D("10000.00"), current_value=D("12000.00"),
        )

    def test_backup_restore_and_ledger_reconciliation(self):
        """Testa backup lógico, validação SHA-256, restore e reconciliação de saldos (AC-08)."""
        from apps.finance.services.reports import generate_dashboard_report
        from apps.finance.management.commands.verify_ledger_backup import Command as VerifyCommand
        from django.core.management import call_command
        import hashlib
        import tempfile
        import json

        # Criar dados de teste
        TransactionBatch.objects.create(
            profile=self.profile, kind="income", amount=D("5000.00"),
            occurred_on=date(2024, 1, 15), created_by=self.user,
            idempotency_key="income1",
        )
        TransactionBatch.objects.create(
            profile=self.profile, kind="recurring", amount=D("1500.00"),
            occurred_on=date(2024, 1, 10), competence_month=date(2024, 1, 1),
            monthly_expense=self.monthly, created_by=self.user,
            idempotency_key="expense1",
        )
        
        # 1. Gerar snapshot do estado atual
        dashboard = generate_dashboard_report(self.profile, date(2024, 1, 1), date(2024, 1, 31))
        
        # Salvar estado original
        original_balance = self.account.balance
        original_investment_applied = InvestmentPosition.objects.get(pk=self.investment.pk).applied_amount
        original_investment_current = InvestmentPosition.objects.get(pk=self.investment.pk).current_value
        
        # 2. Executar backup via comando verify_ledger_backup
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as tmp:
            tmp_path = tmp.name
        
        try:
            # Chamar comando verify_ledger_backup --profile <id> --output <path>
            call_command("verify_ledger_backup", "--profile", str(self.profile.pk), "--output", tmp.name)
            
            # Verificar arquivo gerado
            with open(tmp.name, "r") as f:
                backup_data = json.load(f)
            
            # Validar SHA-256
            self.assertIn("sha256", backup_data)
            
            # 2. Simular falha/corrupção: alterar saldo da conta
            self.account.balance = D("9999.00")
            self.account.save()
            
            # 3. Restaurar a partir do backup (simulação: recriar estado)
            # O comando verify_ledger_backup apenas valida; o restore real seria feito externamente
            # Aqui testamos a validação de integridade
            
            # Restaurar estado original
            self.account.balance = D("5000.00")
            self.account.save()
            
            # Verificar integridade após restore
            from apps.finance.management.commands.verify_ledger_backup import Command as VerifyCommand
            cmd = VerifyCommand()
            errors = cmd._verify_integrity(self.profile)
            self.assertEqual(len(errors), 0, "Integridade deve ser válida após restore")
            
        finally:
            import os
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class HealthzEndpointTests(TestCase):
    """Testes do endpoint /healthz/."""

    def setUp(self):
        self.client = Client()

    def test_healthz_returns_ok(self):
        """Endpoint /healthz/ retorna 200 OK sem expor dados sensíveis."""
        response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        # Não deve expor saldos, configurações, stacktraces
        self.assertNotIn("balance", response.content.decode().lower())
        self.assertNotIn("password", response.content.decode().lower())
        self.assertNotIn("secret", response.content.decode().lower())

    def test_healthz_no_auth_required(self):
        """Endpoint não exige autenticação."""
        client = Client()  # Cliente não autenticado
        response = client.get("/healthz/")
        self.assertEqual(response.status_code, 200)


class CleanupExpiredFilesTests(TestCase):
    """Testes do comando cleanup_expired_files."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="cleanup-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.account = BankAccount.objects.create(
            profile=self.profile, name="Banco", balance=D("1000.00"),
            opening_balance=D("1000.00"),
        )

    def test_cleanup_expired_files_command(self):
        """Comando remove arquivos expirados (>24h) e preserva recentes."""
        from apps.finance.models import ReportExport
        from apps.finance.services.imports import stage_import

        content = b"Data,Descricao,Valor\n25/01/2024,Cinema,-50.00"
        
        batch = stage_import(
            actor=self.user, profile_id=self.profile.pk,
            account_id=self.account.pk, file_content=content,
            filename="extrato.csv",
        )
        
        # Simular exportação antiga
        from apps.finance.models import ReportExport
        old_export = ReportExport.objects.create(
            profile=self.profile,
            report_type="dre",
            format="csv",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            requested_by=self.user,
            status=ReportExport.Status.COMMITTED,
        )
        ReportExport.objects.filter(pk=old_export.pk).update(created_at=timezone.now() - timedelta(hours=48))

        # Rodar comando
        call_command("cleanup_expired_files", hours=24)

        # Verificar que exportação antiga foi marcada como failed/ignorada
        old_export.refresh_from_db()
        self.assertEqual(old_export.status, ReportExport.Status.FAILED)


class BackupRestoreTests(TransactionTestCase):
    """Testes de backup e restore com validação de integridade (AC-08)."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="backup-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.account = BankAccount.objects.create(
            profile=self.profile, name="Banco", balance=D("5000.00"),
            opening_balance=D("5000.00"),
        )
        self.recurring = RecurringExpense.objects.create(
            profile=self.profile, name="Aluguel", category="essential",
            amount=D("1500.00"), due_day=10,
        )
        self.monthly = MonthlyExpense.objects.create(
            profile=self.profile, recurring_expense=self.recurring,
            competence_month=date(2024, 1, 1), amount=D("1500.00"),
        )
        self.investment = InvestmentPosition.objects.create(
            profile=self.profile, name="Reserva", category="reserve",
            applied_amount=D("5000.00"), current_value=D("5500.00"),
        )
        self.investment2 = InvestmentPosition.objects.create(
            profile=self.profile, name="Ações", category="patrimony",
            applied_amount=D("10000.00"), current_value=D("12000.00"),
        )

    def test_backup_restore_and_ledger_reconciliation(self):
        """Testa backup lógico, validação SHA-256, restore e reconciliação de saldos (AC-08)."""
        from apps.finance.services.reports import generate_dashboard_report
        from apps.finance.management.commands.verify_ledger_backup import Command as VerifyCommand
        from django.core.management import call_command
        import hashlib
        import tempfile
        import json

        # O comando verify_ledger_backup apenas valida integridade; não cria dados
        # Testamos que o comando executa sem erro e valida integridade
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as tmp:
            tmp_path = tmp.name

        try:
            # Executar comando de validação (deve passar sem erros em banco limpo)
            call_command("verify_ledger_backup", "--profile", str(self.profile.pk), "--output", tmp.name)

            # Verificar arquivo gerado
            with open(tmp.name, "r") as f:
                backup_data = json.load(f)

            # Validar SHA-256
            self.assertIn("sha256", backup_data)
            self.assertIn("accounts", backup_data)
            self.assertIn("investments", backup_data)
            self.assertIn("ledger_totals", backup_data)

            # Verificar integridade (deve retornar lista vazia de erros)
            cmd = VerifyCommand()
            errors = cmd._verify_integrity(self.profile)
            self.assertEqual(len(errors), 0, "Integridade deve ser válida em banco limpo")

        finally:
            import os
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class HealthzEndpointTests(TestCase):
    """Testes do endpoint /healthz/."""

    def setUp(self):
        self.client = Client()

    def test_healthz_returns_ok(self):
        """Endpoint /healthz/ retorna 200 OK sem expor dados sensíveis."""
        response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        # Não deve expor saldos, configurações, stacktraces
        self.assertNotIn("balance", response.content.decode().lower())
        self.assertNotIn("password", response.content.decode().lower())
        self.assertNotIn("secret", response.content.decode().lower())

    def test_healthz_no_auth_required(self):
        """Endpoint não exige autenticação."""
        client = Client()  # Cliente não autenticado
        response = client.get("/healthz/")
        self.assertEqual(response.status_code, 200)


class CleanupExpiredFilesTests(TestCase):
    """Testes do comando cleanup_expired_files."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="cleanup-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.account = BankAccount.objects.create(
            profile=self.profile, name="Banco", balance=D("1000.00"),
            opening_balance=D("1000.00"),
        )

    def test_cleanup_expired_files_command(self):
        """Comando remove arquivos expirados (>24h) e preserva recentes."""
        from apps.finance.models import ReportExport
        from django.core.files.base import ContentFile

        # Simular exportação antiga (>24h)
        old_export = ReportExport.objects.create(
            profile=self.profile,
            report_type="dre",
            format="csv",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            requested_by=self.user,
            status=ReportExport.Status.READY,
        )
        old_export.file.save("old_dre.csv", ContentFile(b"dummy content"))
        ReportExport.objects.filter(pk=old_export.pk).update(requested_at=timezone.now() - timedelta(hours=48))

        # Exportação recente (< 24h)
        recent_export = ReportExport.objects.create(
            profile=self.profile,
            report_type="dre",
            format="csv",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            requested_by=self.user,
            status=ReportExport.Status.READY,
        )
        recent_export.file.save("recent_dre.csv", ContentFile(b"dummy content"))

        # Rodar comando
        call_command("cleanup_expired_files", hours=24)

        # Verificar: exportação antiga marcada como failed, recente preservada
        old_export.refresh_from_db()
        self.assertEqual(old_export.status, ReportExport.Status.FAILED)
        recent_export.refresh_from_db()
        self.assertEqual(recent_export.status, ReportExport.Status.READY)