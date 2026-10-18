# SPDX-License-Identifier: GPL-3.0-only
"""Testes para Sprint 05: Categorização De-Para, PDF, Relatórios."""
from datetime import date
from decimal import Decimal as D
from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.finance.models import (
    BankAccount, FinancialProfile, ImportBatch, InvestmentPosition, MonthlyExpense,
    RecurringExpense, TransactionBatch, Workspace,
    WorkspaceMembership, CategorizationRule,
)
from apps.finance.services.categorization import (
    create_categorization_rule, update_categorization_rule, delete_categorization_rule,
    get_categorization_rules, apply_rules_to_transactions,
    validate_regex_safety, compile_safe_regex,
    RegexSecurityError,
)
from apps.finance.services.importers import (
    CSVParser, OFX1Parser, PDFParser, detect_format, ImportParseError, ImportSecurityError, ImportFormatError,
)
from apps.finance.services.imports import (
    stage_import, commit_import, dry_run_import, check_duplicates, _suggest_link, _descriptions_match,
)
from apps.finance.services.reports import (
    generate_dre_report, generate_equity_evolution_report,
    generate_investment_report, generate_goals_report, generate_dashboard_report,
)
from apps.finance.services.importers import ParsedTransaction


class CategorizationRuleTests(TestCase):
    """Testes das regras de categorização De-Para."""

    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username="cat-admin")
        self.common = User.objects.create_user(username="cat-common")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.admin)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.admin, role="admin")
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.common, role="common")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Perfil Teste")

    def test_create_exact_match_rule(self):
        """Cria regra de correspondência exata."""
        rule = create_categorization_rule(
            actor=self.admin, workspace_id=self.ws.pk, profile_id=self.profile.pk,
            name="Supermercado", match_type="exact", pattern="supermercado",
            match_field="both", suggested_kind="unexpected",
            suggested_link={}, priority=10,
        )
        self.assertEqual(rule.name, "Supermercado")
        self.assertEqual(rule.match_type, "exact")
        self.assertEqual(rule.pattern, "supermercado")

    def test_create_regex_rule(self):
        """Cria regra com regex válida."""
        rule = create_categorization_rule(
            actor=self.admin, workspace_id=self.ws.pk, profile_id=self.profile.pk,
            name="PIX", match_type="regex", pattern=r"pix|ted|doc",
            match_field="description", suggested_kind="transfer",
            suggested_link={}, priority=5,
        )
        self.assertEqual(rule.match_type, "regex")
        self.assertEqual(rule.pattern, r"pix|ted|doc")

    def test_reject_unsafe_regex(self):
        """Rejeita regex perigosa (ReDoS)."""
        with self.assertRaises(RegexSecurityError):
            create_categorization_rule(
                actor=self.admin, workspace_id=self.ws.pk, profile_id=self.profile.pk,
                name="Perigosa", match_type="regex", pattern=r"(a+)+",
                match_field="description", suggested_kind="unexpected",
                suggested_link={}, priority=10,
            )

    def test_reject_nested_quantifiers(self):
        """Rejeita quantificadores aninhados."""
        with self.assertRaises(RegexSecurityError):
            create_categorization_rule(
                actor=self.admin, workspace_id=self.ws.pk, profile_id=self.profile.pk,
                name="Aninhada", match_type="regex", pattern=r"(a*)*",
                match_field="description", suggested_kind="unexpected",
                suggested_link={}, priority=10,
            )

    def test_update_rule(self):
        """Atualiza regra existente."""
        rule = create_categorization_rule(
            actor=self.admin, workspace_id=self.ws.pk, profile_id=self.profile.pk,
            name="Original", match_type="exact", pattern="teste",
            match_field="description", suggested_kind="unexpected",
            suggested_link={}, priority=10,
        )
        rule = update_categorization_rule(
            actor=self.admin, rule_id=rule.pk, workspace_id=self.ws.pk,
            name="Atualizada", priority=5,
        )
        self.assertEqual(rule.name, "Atualizada")
        self.assertEqual(rule.priority, 5)

    def test_delete_rule(self):
        """Exclui regra."""
        rule = create_categorization_rule(
            actor=self.admin, workspace_id=self.ws.pk, profile_id=self.profile.pk,
            name="Para Excluir", match_type="exact", pattern="excluir",
            match_field="description", suggested_kind="unexpected",
            suggested_link={}, priority=10,
        )
        delete_categorization_rule(
            actor=self.admin, rule_id=rule.pk, workspace_id=self.ws.pk,
        )
        self.assertFalse(CategorizationRule.objects.filter(pk=rule.pk).exists())

    def test_rule_priority_ordering(self):
        """Regras ordenadas por prioridade."""
        create_categorization_rule(
            actor=self.admin, workspace_id=self.ws.pk, profile_id=self.profile.pk,
            name="Baixa", match_type="exact", pattern="baixa",
            match_field="description", suggested_kind="unexpected",
            suggested_link={}, priority=100,
        )
        create_categorization_rule(
            actor=self.admin, workspace_id=self.ws.pk, profile_id=self.profile.pk,
            name="Alta", match_type="exact", pattern="alta",
            match_field="description", suggested_kind="unexpected",
            suggested_link={}, priority=10,
        )
        rules = get_categorization_rules(self.ws.pk, profile_id=self.profile.pk)
        self.assertEqual(rules[0].name, "Alta")
        self.assertEqual(rules[1].name, "Baixa")

    def test_profile_rules_override_workspace(self):
        """Regras de perfil têm precedência sobre núcleo."""
        # Regra do núcleo
        create_categorization_rule(
            actor=self.admin, workspace_id=self.ws.pk, profile_id=None,
            name="Núcleo", match_type="exact", pattern="teste",
            match_field="description", suggested_kind="unexpected",
            suggested_link={}, priority=50,
        )
        # Regra do perfil (prioridade menor mas deve vir primeiro)
        create_categorization_rule(
            actor=self.admin, workspace_id=self.ws.pk, profile_id=self.profile.pk,
            name="Perfil", match_type="exact", pattern="teste",
            match_field="description", suggested_kind="income",
            suggested_link={}, priority=100,
        )
        rules = get_categorization_rules(self.ws.pk, profile_id=self.profile.pk)
        # A primeira regra que casa é a do perfil (prioridade 100 vs 50, mas perfil vem primeiro)
        self.assertEqual(rules[0].name, "Perfil")


class RegexSafetyTests(TestCase):
    """Testes de segurança de regex."""

    def test_validate_safe_regex(self):
        """Valida regex seguras."""
        validate_regex_safety("supermercado")
        validate_regex_safety(r"pix|ted|doc")
        validate_regex_safety(r"\d{2}/\d{2}/\d{4}")

    def test_reject_long_pattern(self):
        """Rejeita padrão muito longo."""
        long_pattern = "a" * 600
        with self.assertRaises(RegexSecurityError):
            validate_regex_safety(long_pattern)

    def test_reject_too_many_groups(self):
        """Rejeita muitos grupos de captura."""
        pattern = "(" + "|".join(["a"] * 15) + ")"
        with self.assertRaises(RegexSecurityError):
            validate_regex_safety(pattern)

    def test_compile_safe_regex(self):
        """Compila regex segura."""
        regex = compile_safe_regex("teste")
        self.assertTrue(regex.search("teste"))
        
        regex = compile_safe_regex("TESTE", case_sensitive=True)
        self.assertTrue(regex.search("TESTE"))
        self.assertFalse(regex.search("teste"))


class PDFParserTests(TestCase):
    """Testes do parser PDF."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="pdf-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.account = BankAccount.objects.create(
            profile=self.profile, name="Banco", balance=D("1000.00"),
            opening_balance=D("1000.00"),
        )

    def test_detect_pdf_format(self):
        """Detecta formato PDF."""
        pdf_content = b"%PDF-1.4\n%...\n%%EOF"
        self.assertEqual(detect_format("extrato.pdf", pdf_content), "pdf")

    def test_reject_invalid_pdf(self):
        """Rejeita PDF inválido."""
        content = b"not a pdf"
        with self.assertRaises(ImportFormatError):
            detect_format("extrato.pdf", content)

    def test_reject_encrypted_pdf(self):
        """Rejeita PDF criptografado."""
        # Criar PDF simples com pymupdf e criptografar
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Test")
        encrypted = BytesIO()
        doc.save(encrypted, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="senha")
        doc.close()
        
        content = encrypted.getvalue()
        parser = PDFParser(self.profile, self.account)
        with self.assertRaises(ImportParseError):
            parser.parse(content, "encrypted.pdf")


class CategorizationIntegrationTests(TestCase):
    """Testes de integração da categorização com importação."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="cat-int-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.account = BankAccount.objects.create(
            profile=self.profile, name="Banco", balance=D("1000.00"),
            opening_balance=D("1000.00"),
        )
        # Criar regra de categorização
        create_categorization_rule(
            actor=self.user, workspace_id=self.ws.pk, profile_id=self.profile.pk,
            name="Mercado", match_type="exact", pattern="supermercado",
            match_field="both", suggested_kind="unexpected",
            suggested_link={}, priority=10,
        )

    def test_apply_rules_to_transactions(self):
        """Aplica regras a transações."""
        
        txns = [
            ParsedTransaction(description="Supermercado ABC", amount=D("150.00"), is_credit=False),
            ParsedTransaction(description="Posto de Gasolina", amount=D("200.00"), is_credit=False),
        ]
        
        txns = apply_rules_to_transactions(txns, self.profile)
        
        self.assertEqual(txns[0].suggested_kind, "unexpected")
        self.assertEqual(txns[0].confidence, D("0.85"))
        self.assertIn("Mercado", txns[0].justification)
        
        # Segunda transação sem regra -> heurística
        self.assertEqual(txns[1].suggested_kind, "unexpected")

    def test_stage_import_applies_rules(self):
        """Stage import aplica regras de categorização."""
        content = b"Data,Descricao,Valor\n15/01/2024,Supermercado ABC,-150.00\n20/01/2024,Posto Gasolina,-200.00"
        
        batch = stage_import(
            actor=self.user, profile_id=self.profile.pk,
            account_id=self.account.pk, file_content=content,
            filename="extrato.csv",
        )
        
        row1 = batch.rows.get(row_number=1)
        row2 = batch.rows.get(row_number=2)
        
        self.assertEqual(row1.suggested_kind, "unexpected")
        self.assertIn("Mercado", row1.justification)
        self.assertEqual(row2.suggested_kind, "unexpected")


class ReportsTests(TestCase):
    """Testes dos relatórios financeiros."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="report-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.account = BankAccount.objects.create(
            profile=self.profile, name="Banco", balance=D("5000.00"),
            opening_balance=D("5000.00"),
        )
        self.account2 = BankAccount.objects.create(
            profile=self.profile, name="Banco2", balance=D("3000.00"),
            opening_balance=D("3000.00"),
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
            target_amount=D("10000.00"),
        )
        self.investment2 = InvestmentPosition.objects.create(
            profile=self.profile, name="Ações", category="patrimony",
            applied_amount=D("10000.00"), current_value=D("12000.00"),
        )

    def test_dre_report(self):
        """Gera DRE report."""
        # Criar receita
        TransactionBatch.objects.create(
            profile=self.profile, kind="income", amount=D("5000.00"),
            occurred_on=date(2024, 1, 15), created_by=self.user,
            idempotency_key="income1",
        )
        # Criar despesa
        TransactionBatch.objects.create(
            profile=self.profile, kind="recurring", amount=D("1500.00"),
            occurred_on=date(2024, 1, 10), competence_month=date(2024, 1, 1),
            monthly_expense=self.monthly, created_by=self.user,
            idempotency_key="expense1",
        )
        
        dre = generate_dre_report(self.profile, date(2024, 1, 1), date(2024, 1, 31))
        
        self.assertEqual(dre.income_received, D("5000.00"))
        self.assertEqual(dre.expenses_confirmed, D("1500.00"))
        self.assertEqual(dre.net_result, D("3500.00"))

    def test_equity_evolution_report(self):
        """Gera evolução patrimonial."""
        equity = generate_equity_evolution_report(
            self.profile, date(2024, 1, 1), date(2024, 3, 31), "month"
        )
        
        self.assertEqual(len(equity.points), 3)  # Jan, Fev, Mar
        self.assertEqual(equity.points[0].bank_balance, D("8000.00"))  # 5000 + 3000
        self.assertEqual(equity.points[0].investment_value, D("17500.00"))  # 5500 + 12000
        self.assertEqual(equity.points[0].net_equity, D("25500.00"))

    def test_investment_report(self):
        """Gera relatório de investimentos."""
        # Criar aplicação
        TransactionBatch.objects.create(
            profile=self.profile, kind="application", amount=D("1000.00"),
            occurred_on=date(2024, 1, 15), investment=self.investment,
            created_by=self.user, idempotency_key="app1",
        )
        # Criar resgate
        TransactionBatch.objects.create(
            profile=self.profile, kind="withdrawal", amount=D("500.00"),
            occurred_on=date(2024, 2, 15), investment=self.investment2,
            created_by=self.user, idempotency_key="wd1",
        )
        
        inv_report = generate_investment_report(
            self.profile, date(2024, 1, 1), date(2024, 12, 31)
        )
        
        self.assertEqual(inv_report.total_applied, D("15000.00"))
        self.assertEqual(inv_report.total_current, D("17500.00"))
        self.assertEqual(inv_report.applications_period, D("1000.00"))
        self.assertEqual(inv_report.withdrawals_period, D("500.00"))

    def test_goals_report(self):
        """Gera relatório de metas."""
        goals = generate_goals_report(self.profile)
        
        self.assertEqual(goals.reserve["current"], D("5500.00"))  # Reserva category
        self.assertEqual(goals.reserve["coverage_months"], 9)
        self.assertEqual(len(goals.goals), 1)  # Ações com target
        self.assertEqual(goals.goals[0]["name"], "Ações")
        self.assertEqual(goals.goals[0]["target"], D("10000.00"))

    def test_dashboard_report(self):
        """Gera dashboard consolidado."""
        dashboard = generate_dashboard_report(
            self.profile, date(2024, 1, 1), date(2024, 1, 31)
        )
        
        self.assertIsNotNone(dashboard.dre)
        self.assertIsNotNone(dashboard.equity)
        self.assertIsNotNone(dashboard.investments)
        self.assertIsNotNone(dashboard.goals)


class DuplicateDetectionTests(TestCase):
    """Testes de detecção de duplicidades."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="dup-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.account = BankAccount.objects.create(
            profile=self.profile, name="Banco", balance=D("1000.00"),
            opening_balance=D("1000.00"),
        )

    def test_duplicate_by_fitid(self):
        """Detecta duplicata por FITID."""
        from apps.finance.services.imports import ParsedStatement, ParsedTransaction
        
        # Batch anterior com FITID
        batch = TransactionBatch.objects.create(
            profile=self.profile, kind="unexpected", amount=D("100.00"),
            occurred_on=date(2024, 1, 15), created_by=self.user,
            idempotency_key="batch1",
        )
        from apps.finance.models import ImportBatch, ImportRow
        ibatch = ImportBatch.objects.create(
            profile=self.profile, account=self.account,
            filename="old.csv", file_hash="hash1", format="csv",
            parser_version="csv-1.0", status="committed", created_by=self.user,
        )
        ImportRow.objects.create(
            batch=ibatch, row_number=1, fitid="FITID123",
            occurred_on=date(2024, 1, 15), description="Teste",
            amount=D("-100.00"), is_credit=False,
            status=ImportRow.Status.COMMITTED, linked_batch=batch,
        )
        
        statement = ParsedStatement()
        statement.transactions.append(ParsedTransaction(
            fitid="FITID123", occurred_on=date(2024, 1, 15),
            description="Teste", amount=D("100.00"), is_credit=False,
        ))
        
        results = check_duplicates(self.profile, self.account, statement, "hash2")
        
        self.assertTrue(results[0].is_duplicate)
        self.assertEqual(results[0].duplicate_type, "fitid")

    def test_same_value_date_not_duplicate(self):
        """Mesmo valor e data não são duplicados automaticamente."""
        from apps.finance.services.imports import ParsedStatement, ParsedTransaction
        
        statement = ParsedStatement()
        statement.transactions.append(ParsedTransaction(
            fitid="FITID1", occurred_on=date(2024, 1, 15),
            description="Mercado A", amount=D("100.00"), is_credit=False,
        ))
        statement.transactions.append(ParsedTransaction(
            fitid="FITID2", occurred_on=date(2024, 1, 15),
            description="Mercado B", amount=D("100.00"), is_credit=False,
        ))
        
        results = check_duplicates(self.profile, self.account, statement, "hash1")
        
        self.assertFalse(results[0].is_duplicate)
        self.assertFalse(results[1].is_duplicate)


class SuggestLinkTests(TestCase):
    """Testes de sugestão de vínculo."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="link-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.account = BankAccount.objects.create(
            profile=self.profile, name="Banco", balance=D("1000.00"),
            opening_balance=D("1000.00"),
        )
        self.recurring = RecurringExpense.objects.create(
            profile=self.profile, name="Aluguel", category="essential",
            amount=D("1000.00"), due_day=5,
        )
        self.monthly = MonthlyExpense.objects.create(
            profile=self.profile, recurring_expense=self.recurring,
            competence_month=date(2024, 1, 1), amount=D("1000.00"),
        )
        self.investment = InvestmentPosition.objects.create(
            profile=self.profile, name="Reserva", category="reserve",
            applied_amount=D("1000.00"), current_value=D("1100.00"),
        )

    def test_suggest_link_recurring(self):
        """Sugere link para despesa recorrente."""
        from apps.finance.services.imports import ParsedTransaction
        
        txn = ParsedTransaction(description="Aluguel Janeiro", amount=D("1000.00"), is_credit=False)
        link = _suggest_link(self.profile, self.account, txn, "recurring")
        
        self.assertIn("recurring_expense_id", link)
        self.assertEqual(link["recurring_expense_id"], self.recurring.pk)

    def test_suggest_link_investment(self):
        """Sugere link para investimento."""
        from apps.finance.services.imports import ParsedTransaction
        
        txn = ParsedTransaction(description="Aplicacao Reserva", amount=D("500.00"), is_credit=False)
        link = _suggest_link(self.profile, self.account, txn, "application")
        
        self.assertIn("investment_id", link)
        self.assertEqual(link["investment_id"], self.investment.pk)

    def test_descriptions_match(self):
        """Testa correspondência de descrições."""
        
        self.assertTrue(_descriptions_match("Aluguel Janeiro", "Aluguel"))
        self.assertTrue(_descriptions_match("Supermercado ABC", "Supermercado"))
        self.assertFalse(_descriptions_match("ABC", "XYZ"))
        self.assertFalse(_descriptions_match("", "teste"))


class DryRunTests(TestCase):
    """Testes de dry-run."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="dry-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.account = BankAccount.objects.create(
            profile=self.profile, name="Banco", balance=D("1000.00"),
            opening_balance=D("1000.00"),
        )

    def test_dry_run_validates_without_saving(self):
        """Dry-run valida sem gravar no banco."""
        
        content = b"Data,Descricao,Valor\n25/01/2024,Cinema,-50.00"
        
        mock_batch, suggestions = dry_run_import(
            actor=self.user, profile_id=self.profile.pk,
            account_id=self.account.pk, file_content=content,
            filename="extrato.csv",
        )
        
        self.assertEqual(mock_batch.total_rows, 1)
        self.assertEqual(len(suggestions), 1)
        # Verificar que nada foi salvo no banco
        from apps.finance.models import ImportBatch
        self.assertEqual(ImportBatch.objects.count(), 0)


class CommitImportTests(TestCase):
    """Testes de commit de importação."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="commit-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.account = BankAccount.objects.create(
            profile=self.profile, name="Banco", balance=D("1000.00"),
            opening_balance=D("1000.00"),
        )

    def test_commit_create_new_unexpected(self):
        """Commit cria nova despesa imprevisível."""
        from apps.finance.services.imports import stage_import
        
        content = b"Data,Descricao,Valor\n25/01/2024,Cinema,-50.00"
        batch = stage_import(
            actor=self.user, profile_id=self.profile.pk,
            account_id=self.account.pk, file_content=content,
            filename="extrato.csv",
        )
        
        row = batch.rows.first()
        row_decisions = [{
            "row_id": row.pk,
            "action": "create_new",
            "adjusted_amount": "50.00",
            "splits": {self.account.pk: D("50.00")},
        }]
        
        batch = commit_import(
            actor=self.user, batch_id=batch.pk,
            row_decisions=row_decisions,
            idempotency_key="commit1",
        )
        
        self.assertEqual(batch.status, "committed")
        self.assertTrue(TransactionBatch.objects.filter(kind="unexpected", amount=D("50.00")).exists())

    def test_commit_idempotency(self):
        """Commit é idempotente com mesma chave."""
        from apps.finance.services.imports import stage_import
        
        content = b"Data,Descricao,Valor\n25/01/2024,Cinema,-50.00"
        batch = stage_import(
            actor=self.user, profile_id=self.profile.pk,
            account_id=self.account.pk, file_content=content,
            filename="extrato.csv",
        )
        
        row = batch.rows.first()
        row_decisions = [{
            "row_id": row.pk,
            "action": "create_new",
            "adjusted_amount": "50.00",
            "splits": {self.account.pk: D("50.00")},
        }]
        
        commit_import(
            actor=self.user, batch_id=batch.pk,
            row_decisions=row_decisions,
            idempotency_key="idem-key",
        )
        
        # Segundo commit com mesma chave deve falhar
        ImportBatch.objects.get(pk=batch.pk)
        with self.assertRaises(Exception):
            commit_import(
                actor=self.user, batch_id=batch.pk,
                row_decisions=row_decisions,
                idempotency_key="idem-key",
            )


class ImportPermissionTests(TestCase):
    """Testes de permissões para importação."""

    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username="admin")
        self.common = User.objects.create_user(username="common")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.admin)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.admin, role="admin")
        self.member = WorkspaceMembership.objects.create(workspace=self.ws, user=self.common, role="common")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.account = BankAccount.objects.create(
            profile=self.profile, name="Banco", balance=D("1000.00"),
            opening_balance=D("1000.00"),
        )

    def test_common_cannot_import_without_grants(self):
        """Comum sem grants não pode importar."""
        from apps.finance.services.imports import stage_import
        
        content = b"Data,Descricao,Valor\n25/01/2024,Cinema,-50.00"
        
        with self.assertRaises(Exception):  # PermissionDenied
            stage_import(
                actor=self.common, profile_id=self.profile.pk,
                account_id=self.account.pk, file_content=content,
                filename="extrato.csv",
            )

    def test_common_with_grants_can_import(self):
        """Comum com grants pode importar."""
        from apps.finance.services.grants import save_grant, GRANT_FIELDS
        from apps.finance.services.imports import stage_import
        
        save_grant(
            actor=self.admin, profile_id=self.profile.pk,
            membership_id=self.member.pk,
            levels={**{f: "none" for f in GRANT_FIELDS},
                    "accounts_level": "edit", "movements_level": "edit"},
        )
        
        content = b"Data,Descricao,Valor\n25/01/2024,Cinema,-50.00"
        
        batch = stage_import(
            actor=self.common, profile_id=self.profile.pk,
            account_id=self.account.pk, file_content=content,
            filename="extrato.csv",
        )
        
        self.assertEqual(batch.status, "validated")


class SecurityTests(TestCase):
    """Testes de segurança da importação."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="sec-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.account = BankAccount.objects.create(
            profile=self.profile, name="Banco", balance=D("1000.00"),
            opening_balance=D("1000.00"),
        )

    def test_reject_oversized_file(self):
        """Rejeita arquivo maior que 5 MiB."""
        from apps.finance.services.imports import stage_import
        
        large_content = b"x" * (6 * 1024 * 1024)
        
        with self.assertRaises(ImportSecurityError):
            stage_import(
                actor=self.user, profile_id=self.profile.pk,
                account_id=self.account.pk, file_content=large_content,
                filename="grande.csv",
            )

    def test_sanitizes_description(self):
        """Sanitiza descrição removendo caracteres de controle."""
        from apps.finance.services.imports import stage_import
        
        content = b"Data,Descricao,Valor\n15/01/2024,Teste\x00\x1f,-100.00"
        
        batch = stage_import(
            actor=self.user, profile_id=self.profile.pk,
            account_id=self.account.pk, file_content=content,
            filename="extrato.csv",
        )
        
        row = batch.rows.first()
        self.assertNotIn("\x00", row.description)
        self.assertNotIn("\x1f", row.description)


class EdgeCaseTests(TestCase):
    """Testes de casos de borda."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="edge-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.account = BankAccount.objects.create(
            profile=self.profile, name="Banco", balance=D("1000.00"),
            opening_balance=D("1000.00"),
        )

    def test_csv_with_negative_values(self):
        """CSV com valores negativos explícitos."""
        
        content = b"Data,Descricao,Valor\n15/01/2024,Debito,-100.00\n16/01/2024,Credito,+200.00"
        
        parser = CSVParser(self.profile, self.account)
        statement = parser.parse(content, "test.csv")
        
        self.assertEqual(len(statement.transactions), 2)
        self.assertFalse(statement.transactions[0].is_credit)
        self.assertTrue(statement.transactions[1].is_credit)

    def test_ofx_malformed(self):
        """OFX malformado."""
        
        content = b"<OFX><BANKMSGSRSV1><STMTTRNRS>"
        
        parser = OFX1Parser(self.profile)
        
        with self.assertRaises(ImportParseError):
            parser.parse(content, "malformed.ofx")

    def test_same_value_date_different_transactions(self):
        """Mesmo valor e data não são automaticamente duplicados."""
        from apps.finance.services.imports import ParsedStatement, ParsedTransaction
        
        statement = ParsedStatement()
        statement.transactions.append(ParsedTransaction(
            fitid="FITID1", occurred_on=date(2024, 1, 15),
            description="Mercado A", amount=D("100.00"), is_credit=False,
        ))
        statement.transactions.append(ParsedTransaction(
            fitid="FITID2", occurred_on=date(2024, 1, 15),
            description="Mercado B", amount=D("100.00"), is_credit=False,
        ))
        
        results = check_duplicates(self.profile, self.account, statement, "hash1")
        
        self.assertFalse(results[0].is_duplicate)
        self.assertFalse(results[1].is_duplicate)


class IntegrationTests(TestCase):
    """Testes de integração completa."""

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="int-test")
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
            applied_amount=D("1000.00"), current_value=D("1100.00"),
        )

    def test_full_import_workflow_csv(self):
        """Fluxo completo: upload -> stage -> preview -> commit."""
        from apps.finance.services.imports import (
            stage_import, generate_reconciliation_suggestions,
        )
        
        content = b"""Data,Descricao,Valor
10/01/2024,Aluguel,-500.00
15/01/2024,Aplicacao Reserva,-1000.00
20/01/2024,Supermercado,-300.00"""
        
        batch = stage_import(
            actor=self.user, profile_id=self.profile.pk,
            account_id=self.account.pk, file_content=content,
            filename="extrato_completo.csv",
        )
        
        self.assertEqual(batch.total_rows, 3)
        self.assertEqual(batch.valid_rows, 3)
        
        suggestions = generate_reconciliation_suggestions(batch)
        self.assertEqual(len(suggestions), 3)
        
        self.assertEqual(suggestions[0].action, "partial_payment")
        self.assertEqual(suggestions[1].action, "link_existing")
        self.assertEqual(suggestions[2].action, "create_new")
        
        row_decisions = []
        for i, row in enumerate(batch.rows.all()):
            if i == 0:
                row_decisions.append({
                    "row_id": row.pk, "action": "partial_payment",
                    "target_expense_id": self.monthly.pk,
                    "adjusted_amount": "500.00",
                    "splits": {self.account.pk: D("500.00")},
                })
            elif i == 1:
                row_decisions.append({
                    "row_id": row.pk, "action": "link_existing",
                    "target_investment_id": self.investment.pk,
                    "adjusted_amount": "1000.00",
                    "splits": {self.account.pk: D("1000.00")},
                })
            else:
                row_decisions.append({
                    "row_id": row.pk, "action": "create_new",
                    "adjusted_amount": "300.00", "adjusted_kind": "unexpected",
                    "splits": {self.account.pk: D("300.00")},
                })
        
        batch = commit_import(
            actor=self.user, batch_id=batch.pk,
            row_decisions=row_decisions,
            idempotency_key="full-workflow",
        )
        
        self.assertEqual(batch.status, "committed")
        self.assertEqual(batch.rows.filter(status="committed").count(), 3)
        
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, D("3200.00"))
        
        self.investment.refresh_from_db()
        self.assertEqual(self.investment.applied_amount, D("2000.00"))
        self.assertEqual(self.investment.current_value, D("2100.00"))
    
    def test_concurrent_import_idempotency(self):
        """Reimportação concorrente não duplica."""
        from apps.finance.services.imports import stage_import
        
        content = b"Data,Descricao,Valor\n25/01/2024,Cinema,-50.00"
        
        batch1 = stage_import(
            actor=self.user, profile_id=self.profile.pk,
            account_id=self.account.pk, file_content=content,
            filename="extrato.csv",
        )
        commit_import(
            actor=self.user, batch_id=batch1.pk,
            row_decisions=[{
                "row_id": batch1.rows.first().pk,
                "action": "create_new",
                "adjusted_amount": "50.00",
                "splits": {self.account.pk: D("50.00")},
            }],
            idempotency_key="idem-test",
        )
        
        with self.assertRaises(Exception):
            stage_import(
                actor=self.user, profile_id=self.profile.pk,
                account_id=self.account.pk, file_content=content,
                filename="extrato.csv",
            )


class PermissionTests(TestCase):
    """Testes de permissões granulares."""

    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username="admin")
        self.common = User.objects.create_user(username="common")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.admin)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.admin, role="admin")
        self.member = WorkspaceMembership.objects.create(workspace=self.ws, user=self.common, role="common")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.account = BankAccount.objects.create(
            profile=self.profile, name="Banco", balance=D("1000.00"),
            opening_balance=D("1000.00"),
        )

    def test_revocation_blocks_next_import(self):
        """Revogação bloqueia próxima importação."""
        from apps.finance.services.grants import save_grant, GRANT_FIELDS
        from apps.finance.services.imports import stage_import
        
        save_grant(
            actor=self.admin, profile_id=self.profile.pk,
            membership_id=self.member.pk,
            levels={**{f: "none" for f in GRANT_FIELDS},
                    "accounts_level": "edit", "movements_level": "edit"},
        )
        
        content = b"Data,Descricao,Valor\n25/01/2024,Cinema,-50.00"
        
        stage_import(
            actor=self.common, profile_id=self.profile.pk,
            account_id=self.account.pk, file_content=content,
            filename="extrato1.csv",
        )
        
        save_grant(
            actor=self.admin, profile_id=self.profile.pk,
            membership_id=self.member.pk,
            levels={f: "none" for f in GRANT_FIELDS},
        )
        
        with self.assertRaises(Exception):
            stage_import(
                actor=self.common, profile_id=self.profile.pk,
                account_id=self.account.pk, file_content=content,
                filename="extrato2.csv",
            )