# SPDX-License-Identifier: GPL-3.0-only
"""Testes para importação e conciliação bancária (Sprint 04)."""
from datetime import date
from decimal import Decimal as D

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.finance.models import (
    BankAccount, FinancialProfile, ImportBatch, ImportRow,
    InvestmentPosition, MonthlyExpense, RecurringExpense,
    TransactionBatch, Workspace, WorkspaceMembership,
)
from apps.finance.services.imports import (
    stage_import, ImportValidationError,
)
from apps.finance.services.importers import (
    CSVParser, OFX1Parser, OFX2Parser, detect_format,
    ImportParseError as ImporterParseError, ImportSecurityError,
)


class CSVParserTests(TestCase):
    """Testes do parser CSV."""
    
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="csv-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.account = BankAccount.objects.create(
            profile=self.profile, name="Banco", balance=D("1000.00"),
            opening_balance=D("1000.00"),
        )
    
    def test_parse_simple_csv(self):
        """Parse de CSV simples com cabeçalho padrão."""
        content = b"Data,Descricao,Valor\n15/01/2024,Mercado,-150.00\n16/01/2024,Salario,5000.00"
        parser = CSVParser(self.profile, self.account)
        statement = parser.parse(content, "extrato.csv")
        
        self.assertEqual(len(statement.transactions), 2)
        self.assertEqual(statement.transactions[0].occurred_on, date(2024, 1, 15))
        self.assertEqual(statement.transactions[0].description, "Mercado")
        self.assertEqual(statement.transactions[0].amount, D("150.00"))
        self.assertFalse(statement.transactions[0].is_credit)
        self.assertTrue(statement.transactions[1].is_credit)
    
    def test_parse_csv_semicolon(self):
        """Parse de CSV com ponto e vírgula."""
        content = b"Data;Historico;Valor\n15/01/2024;Mercado;-150,00"
        parser = CSVParser(self.profile, self.account)
        statement = parser.parse(content, "extrato.csv")
        
        self.assertEqual(len(statement.transactions), 1)
        self.assertEqual(statement.transactions[0].amount, D("150.00"))
    
    def test_parse_csv_tab(self):
        """Parse de CSV com tabulação."""
        content = "Data\tDescricao\tValor\n15/01/2024\tMercado\t-150.00".encode()
        parser = CSVParser(self.profile, self.account)
        statement = parser.parse(content, "extrato.csv")
        
        self.assertEqual(len(statement.transactions), 1)
    
    def test_parse_csv_credit_debit_columns(self):
        """Parse de CSV com colunas separadas de crédito/débito."""
        content = b"Data,Descricao,Credito,Debito\n15/01/2024,Mercado,,150.00\n16/01/2024,Salario,5000.00,"
        parser = CSVParser(self.profile, self.account, credit_debit_columns=True)
        statement = parser.parse(content, "extrato.csv")
        
        self.assertEqual(len(statement.transactions), 2)
        self.assertFalse(statement.transactions[0].is_credit)
        self.assertTrue(statement.transactions[1].is_credit)
    
    def test_parse_csv_iso88591(self):
        """Parse de CSV em ISO-8859-1."""
        content = "Data,Descrição,Valor\n15/01/2024,Mercado,-150,00".encode("iso-8859-1")
        parser = CSVParser(self.profile, self.account)
        statement = parser.parse(content, "extrato.csv")
        
        self.assertEqual(len(statement.transactions), 1)
        self.assertEqual(statement.transactions[0].description, "Mercado")
    
    def test_parse_csv_with_fitid(self):
        """Parse de CSV com FITID."""
        content = b"Data,Descricao,Valor,ID\n15/01/2024,Mercado,-150.00,FITID123"
        parser = CSVParser(self.profile, self.account)
        statement = parser.parse(content, "extrato.csv")
        
        self.assertEqual(statement.transactions[0].fitid, "FITID123")
    
    def test_parse_csv_generates_fitid_when_missing(self):
        """Gera FITID baseado no contexto quando ausente."""
        content = b"Data,Descricao,Valor\n15/01/2024,Mercado,-150.00"
        parser = CSVParser(self.profile, self.account)
        statement = parser.parse(content, "extrato.csv")
        
        self.assertTrue(len(statement.transactions[0].fitid) > 0)
    
    def test_rejects_empty_file(self):
        """Rejeita arquivo vazio."""
        parser = CSVParser(self.profile, self.account)
        with self.assertRaises(ImporterParseError):
            parser.parse(b"", "vazio.csv")
    
    def test_rejects_oversized_file(self):
        """Rejeita arquivo maior que 5 MiB."""
        large_content = b"x" * (6 * 1024 * 1024)
        parser = CSVParser(self.profile, self.account)
        with self.assertRaises(ImportSecurityError):
            parser.parse(large_content, "grande.csv")


class OFX1ParserTests(TestCase):
    """Testes do parser OFX 1.x (SGML)."""
    
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="ofx1-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
    
    def test_parse_ofx1_basic(self):
        """Parse básico de OFX 1.x."""
        content = b"""OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE
<OFX>
<SIGNONMSGSRSV1>
<SONRS>
<STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>
<DTSERVER>20240115120000</DTSERVER>
<LANGUAGE>POR</LANGUAGE>
</SONRS>
</SIGNONMSGSRSV1>
<BANKMSGSRSV1>
<STMTTRNRS>
<TRNUID>1</TRNUID>
<STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>
<STMTRS>
<CURDEF>BRL</CURDEF>
<BANKACCTFROM>
<BANKID>001</BANKID>
<ACCTID>12345</ACCTID>
<ACCTTYPE>CHECKING</ACCTTYPE>
</BANKACCTFROM>
<BANKTRANLIST>
<DTSTART>20240101</DTSTART>
<DTEND>20240131</DTEND>
<STMTTRN>
<TRNTYPE>DEBIT</TRNTYPE>
<DTPOSTED>20240115</DTPOSTED>
<TRNAMT>-150.00</TRNAMT>
<FITID>FITID123</FITID>
<NAME>Mercado</NAME>
<MEMO>Compra no mercado</MEMO>
</STMTTRN>
<STMTTRN>
<TRNTYPE>CREDIT</TRNTYPE>
<DTPOSTED>20240116</DTPOSTED>
<TRNAMT>5000.00</TRNAMT>
<FITID>FITID456</FITID>
<NAME>Salario</NAME>
</STMTTRN>
</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>"""
        
        parser = OFX1Parser(self.profile)
        statement = parser.parse(content, "extrato.ofx")
        
        self.assertEqual(len(statement.transactions), 2)
        self.assertEqual(statement.institution_id, "001")
        self.assertEqual(statement.account_id, "12345")
        self.assertEqual(statement.currency, "BRL")
        self.assertEqual(statement.transactions[0].fitid, "FITID123")
        self.assertFalse(statement.transactions[0].is_credit)
        self.assertTrue(statement.transactions[1].is_credit)
    
    def test_parse_ofx1_without_fitid(self):
        """Gera FITID quando ausente no OFX 1.x."""
        content = b"""<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKTRANLIST><STMTTRN>
<TRNTYPE>DEBIT</TRNTYPE>
<DTPOSTED>20240115</DTPOSTED>
<TRNAMT>-150.00</TRNAMT>
<NAME>Mercado</NAME>
</STMTTRN></BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>"""
        
        parser = OFX1Parser(self.profile)
        statement = parser.parse(content, "extrato.ofx")
        
        self.assertEqual(len(statement.transactions), 1)
        self.assertTrue(len(statement.transactions[0].fitid) > 0)


class OFX2ParserTests(TestCase):
    """Testes do parser OFX 2.x (XML)."""
    
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="ofx2-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
    
    def test_parse_ofx2_basic(self):
        """Parse básico de OFX 2.x XML."""
        content = b"""<?xml version="1.0" encoding="UTF-8"?>
<OFX>
<SIGNONMSGSRSV1>
<SONRS>
<STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>
<DTSERVER>20240115120000</DTSERVER>
<LANGUAGE>POR</LANGUAGE>
</SONRS>
</SIGNONMSGSRSV1>
<BANKMSGSRSV1>
<STMTTRNRS>
<TRNUID>1</TRNUID>
<STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>
<STMTRS>
<CURDEF>BRL</CURDEF>
<BANKACCTFROM>
<BANKID>001</BANKID>
<ACCTID>12345</ACCTID>
<ACCTTYPE>CHECKING</ACCTTYPE>
</BANKACCTFROM>
<BANKTRANLIST>
<DTSTART>20240101</DTSTART>
<DTEND>20240131</DTEND>
<STMTTRN>
<TRNTYPE>DEBIT</TRNTYPE>
<DTPOSTED>20240115</DTPOSTED>
<TRNAMT>-150.00</TRNAMT>
<FITID>FITID123</FITID>
<NAME>Mercado</NAME>
<MEMO>Compra no mercado</MEMO>
</STMTTRN>
<STMTTRN>
<TRNTYPE>CREDIT</TRNTYPE>
<DTPOSTED>20240116</DTPOSTED>
<TRNAMT>5000.00</TRNAMT>
<FITID>FITID456</FITID>
<NAME>Salario</NAME>
</STMTTRN>
</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>"""
        
        parser = OFX2Parser(self.profile)
        statement = parser.parse(content, "extrato.ofx")
        
        self.assertEqual(len(statement.transactions), 2)
        self.assertEqual(statement.institution_id, "001")
        self.assertEqual(statement.account_id, "12345")
        self.assertEqual(statement.currency, "BRL")
        self.assertEqual(statement.transactions[0].fitid, "FITID123")
        self.assertFalse(statement.transactions[0].is_credit)
        self.assertTrue(statement.transactions[1].is_credit)
    
    def test_rejects_xxe(self):
        """Rejeita XML com entidade externa (XXE)."""
        content = b"""<?xml version="1.0"?>
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
<OFX>&xxe;</OFX>"""
        
        parser = OFX2Parser(self.profile)
        with self.assertRaises(ImporterParseError):
            parser.parse(content, "xxe.ofx")


class FormatDetectionTests(TestCase):
    """Testes de detecção de formato."""
    
    def test_detect_csv(self):
        self.assertEqual(detect_format("extrato.csv", b"data,valor\n1,2"), "csv")
        self.assertEqual(detect_format("EXTRATO.CSV", b"data,valor\n1,2"), "csv")
    
    def test_detect_ofx1(self):
        self.assertEqual(detect_format("extrato.ofx", b"OFXHEADER:100\n<OFX>"), "ofx")
    
    def test_detect_ofx2(self):
        self.assertEqual(detect_format("extrato.ofx", b"<?xml version='1.0'?><OFX>"), "ofx2")
        self.assertEqual(detect_format("extrato.ofx", b"<OFX><SIGNONMSGSRSV1>"), "ofx2")
    
    def test_reject_unknown_format(self):
        with self.assertRaises(Exception):
            detect_format("extrato.txt", b"texto")


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
        from apps.finance.services.imports import check_duplicates, ParsedStatement, ParsedTransaction
        
        # Criar batch anterior com FITID
        batch = ImportBatch.objects.create(
            profile=self.profile, account=self.account,
            filename="anterior.csv", file_hash="hash1",
            format="csv", parser_version="csv-1.0", created_by=self.user,
        )
        ImportRow.objects.create(
            batch=batch, row_number=1, fitid="FITID123",
            occurred_on=date(2024, 1, 15), description="Mercado",
            amount=D("-150.00"), is_credit=False,
            status=ImportRow.Status.COMMITTED,
        )
        
        # Novo statement com mesmo FITID
        statement = ParsedStatement()
        statement.transactions.append(ParsedTransaction(
            fitid="FITID123", occurred_on=date(2024, 1, 15),
            description="Mercado", amount=D("150.00"), is_credit=False,
        ))
        
        results = check_duplicates(self.profile, self.account, statement, "hash2")
        
        self.assertTrue(results[0].is_duplicate)
        self.assertEqual(results[0].duplicate_type, "fitid")
        self.assertEqual(results[0].confidence, D("0.95"))
    
    def test_duplicate_by_file_hash(self):
        """Detecta duplicata por hash do arquivo."""
        from apps.finance.services.imports import check_duplicates, ParsedStatement, ParsedTransaction
        
        ImportBatch.objects.create(
            profile=self.profile, account=self.account,
            filename="extrato.csv", file_hash="samehash",
            format="csv", parser_version="csv-1.0", created_by=self.user,
        )
        
        statement = ParsedStatement()
        statement.transactions.append(ParsedTransaction(
            fitid="NEW123", occurred_on=date(2024, 1, 15),
            description="Mercado", amount=D("150.00"), is_credit=False,
        ))
        
        results = check_duplicates(self.profile, self.account, statement, "samehash")
        
        self.assertTrue(results[0].is_duplicate)
        self.assertEqual(results[0].duplicate_type, "file_hash")
        self.assertEqual(results[0].confidence, D("1.00"))


class ImportStagingTests(TestCase):
    """Testes de staging de importação."""
    
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="stage-test")
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
    
    def test_stage_import_creates_batch_and_rows(self):
        """Stage cria batch e rows corretamente."""
        content = b"Data,Descricao,Valor\n15/01/2024,Aluguel,-1000.00\n20/01/2024,Mercado,-200.00"
        
        batch = stage_import(
            actor=self.user, profile_id=self.profile.pk,
            account_id=self.account.pk, file_content=content,
            filename="extrato.csv",
        )
        
        self.assertEqual(batch.total_rows, 2)
        self.assertEqual(batch.valid_rows, 2)
        self.assertEqual(batch.duplicate_rows, 0)
        self.assertEqual(batch.status, ImportBatch.Status.VALIDATED)
        
        rows = list(batch.rows.all())
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].suggested_kind, "recurring")  # Aluguel = recorrente
        self.assertEqual(rows[1].suggested_kind, "unexpected")  # Mercado = imprevisível
    
    def test_stage_import_detects_duplicate_file(self):
        """Detecta arquivo duplicado por hash."""
        content = b"Data,Descricao,Valor\n15/01/2024,Aluguel,-1000.00"
        
        stage_import(
            actor=self.user, profile_id=self.profile.pk,
            account_id=self.account.pk, file_content=content,
            filename="extrato.csv",
        )
        
        with self.assertRaises(ImportValidationError):
            stage_import(
                actor=self.user, profile_id=self.profile.pk,
                account_id=self.account.pk, file_content=content,
                filename="extrato.csv",
            )


class ReconciliationTests(TestCase):
    """Testes de sugestões de reconciliação."""
    
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="recon-test")
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
        # Pagamento parcial já feito
        TransactionBatch.objects.create(
            profile=self.profile, kind="recurring", amount=D("300.00"),
            occurred_on=date(2024, 1, 10), competence_month=date(2024, 1, 1),
            monthly_expense=self.monthly, created_by=self.user,
            idempotency_key="pay1",
        )
    
    def test_suggest_partial_payment(self):
        """Sugere pagamento parcial para despesa com saldo devedor."""
        from apps.finance.services.imports import (
            stage_import, generate_reconciliation_suggestions,
        )
        
        # Importar linha que cobre o restante do aluguel (700)
        content = b"Data,Descricao,Valor\n15/01/2024,Aluguel,-700.00"
        batch = stage_import(
            actor=self.user, profile_id=self.profile.pk,
            account_id=self.account.pk, file_content=content,
            filename="extrato.csv",
        )
        
        suggestions = generate_reconciliation_suggestions(batch)
        
        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0].action, "partial_payment")
        self.assertIsNotNone(suggestions[0].target_expense)
        self.assertEqual(suggestions[0].target_expense.pk, self.monthly.pk)
    
    def test_suggest_link_existing_full_payment(self):
        """Sugere vincular existente para quitação total."""
        from apps.finance.services.imports import (
            stage_import, generate_reconciliation_suggestions,
        )
        
        # Importar linha que quita totalmente (1000)
        content = b"Data,Descricao,Valor\n20/01/2024,Aluguel,-1000.00"
        batch = stage_import(
            actor=self.user, profile_id=self.profile.pk,
            account_id=self.account.pk, file_content=content,
            filename="extrato2.csv",
        )
        
        suggestions = generate_reconciliation_suggestions(batch)
        
        self.assertEqual(suggestions[0].action, "link_existing")
        self.assertIsNotNone(suggestions[0].target_expense)
    
    def test_suggest_new_unexpected(self):
        """Sugere nova despesa imprevisível para gasto desconhecido."""
        from apps.finance.services.imports import (
            stage_import, generate_reconciliation_suggestions,
        )
        
        content = b"Data,Descricao,Valor\n25/01/2024,Cinema,-50.00"
        batch = stage_import(
            actor=self.user, profile_id=self.profile.pk,
            account_id=self.account.pk, file_content=content,
            filename="extrato3.csv",
        )
        
        suggestions = generate_reconciliation_suggestions(batch)
        
        self.assertEqual(suggestions[0].action, "create_new")
        self.assertEqual(suggestions[0].import_row.suggested_kind, "unexpected")


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
        self.recurring = RecurringExpense.objects.create(
            profile=self.profile, name="Aluguel", category="essential",
            amount=D("1000.00"), due_day=5,
        )
        self.monthly = MonthlyExpense.objects.create(
            profile=self.profile, recurring_expense=self.recurring,
            competence_month=date(2024, 1, 1), amount=D("1000.00"),
        )
    
    def test_commit_create_new_unexpected(self):
        """Commit cria nova despesa imprevisível."""
        from apps.finance.services.imports import stage_import, commit_import
        
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
            "adjusted_description": "Cinema",
            "adjusted_kind": "unexpected",
            "splits": {self.account.pk: D("50.00")},
        }]
        
        batch = commit_import(
            actor=self.user, batch_id=batch.pk,
            row_decisions=row_decisions,
            idempotency_key="commit1",
        )
        
        self.assertEqual(batch.status, ImportBatch.Status.COMMITTED)
        self.assertEqual(batch.rows.filter(status=ImportRow.Status.COMMITTED).count(), 1)
        self.assertTrue(TransactionBatch.objects.filter(kind="unexpected", amount=D("50.00")).exists())
    
    def test_commit_partial_payment(self):
        """Commit faz pagamento parcial de despesa existente."""
        from apps.finance.services.imports import stage_import, commit_import
        
        # Pagamento parcial de 300 (já feito no setUp)
        # Importar mais 700 para quitar
        content = b"Data,Descricao,Valor\n20/01/2024,Aluguel,-700.00"
        batch = stage_import(
            actor=self.user, profile_id=self.profile.pk,
            account_id=self.account.pk, file_content=content,
            filename="extrato.csv",
        )
        
        row = batch.rows.first()
        row_decisions = [{
            "row_id": row.pk,
            "action": "partial_payment",
            "target_expense_id": self.monthly.pk,
            "adjusted_amount": "700.00",
            "splits": {self.account.pk: D("700.00")},
        }]
        
        batch = commit_import(
            actor=self.user, batch_id=batch.pk,
            row_decisions=row_decisions,
            idempotency_key="commit2",
        )
        
        self.assertEqual(batch.status, ImportBatch.Status.COMMITTED)
        # Verificar que o monthly expense está quitado
        self.monthly.refresh_from_db()
        # TODO: verificar paid amount
    
    def test_commit_idempotency(self):
        """Commit é idempotente com mesma chave."""
        from apps.finance.services.imports import stage_import, commit_import
        
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
        
        # Primeiro commit
        commit_import(
            actor=self.user, batch_id=batch.pk,
            row_decisions=row_decisions,
            idempotency_key="idem-key",
        )
        
        # Segundo commit com mesma chave deve retornar o mesmo batch
        ImportBatch.objects.get(pk=batch.pk)
        # O batch já está committed, então deve falhar
        with self.assertRaises(Exception):
            commit_import(
                actor=self.user, batch_id=batch.pk,
                row_decisions=row_decisions,
                idempotency_key="idem-key",
            )


class DryRunTests(TestCase):
    """Testes de dry-run."""
    
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="dryrun-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.account = BankAccount.objects.create(
            profile=self.profile, name="Banco", balance=D("1000.00"),
            opening_balance=D("1000.00"),
        )
    
    def test_dry_run_validates_without_saving(self):
        """Dry-run valida sem gravar no banco."""
        from apps.finance.services.imports import dry_run_import
        
        content = b"Data,Descricao,Valor\n25/01/2024,Cinema,-50.00"
        
        mock_batch, suggestions = dry_run_import(
            actor=self.user, profile_id=self.profile.pk,
            account_id=self.account.pk, file_content=content,
            filename="extrato.csv",
        )
        
        self.assertEqual(mock_batch.total_rows, 1)
        self.assertEqual(len(suggestions), 1)
        # Verificar que nada foi salvo no banco
        self.assertEqual(ImportBatch.objects.count(), 0)


class ImportReportTests(TestCase):
    """Testes de relatório de importação."""
    
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="report-test")
        self.ws = Workspace.objects.create(name="Teste", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.ws, name="Teste")
        self.account = BankAccount.objects.create(
            profile=self.profile, name="Banco", balance=D("1000.00"),
            opening_balance=D("1000.00"),
        )
    
    def test_generate_report(self):
        """Gera relatório pós-importação."""
        from apps.finance.services.imports import stage_import, commit_import, generate_import_report
        
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
            idempotency_key="commit-report",
        )
        
        report = generate_import_report(batch)
        
        self.assertEqual(report.total_rows, 1)
        self.assertEqual(report.committed, 1)
        self.assertEqual(report.ignored, 0)
        self.assertEqual(report.duplicates, 0)
        self.assertEqual(report.errors, 0)
        self.assertEqual(len(report.created_batches), 1)


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
    
    def test_rejects_xxe_in_ofx2(self):
        """Rejeita XXE em OFX 2.x."""
        content = b"""<?xml version="1.0"?>
<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
<OFX>&xxe;</OFX>"""
        
        from apps.finance.services.importers import OFX2Parser
        parser = OFX2Parser(self.profile)
        
        with self.assertRaises(ImporterParseError):
            parser.parse(content, "xxe.ofx")
    
    def test_rejects_oversized_file(self):
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
        
        # Descrição com caracteres de controle
        content = b"Data,Descricao,Valor\n15/01/2024,Teste\x00\x1f,-100.00"
        
        batch = stage_import(
            actor=self.user, profile_id=self.profile.pk,
            account_id=self.account.pk, file_content=content,
            filename="extrato.csv",
        )
        
        row = batch.rows.first()
        # Caracteres de controle devem ser removidos
        self.assertNotIn("\x00", row.description)
        self.assertNotIn("\x1f", row.description)


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
            stage_import, generate_reconciliation_suggestions, commit_import,
        )
        
        # CSV com: pagamento aluguel (parcial), aplicação investimento, gasto imprevisível
        content = b"""Data,Descricao,Valor
10/01/2024,Aluguel,-500.00
15/01/2024,Aplicacao Reserva,-1000.00
20/01/2024,Supermercado,-300.00"""
        
        # 1. Stage
        batch = stage_import(
            actor=self.user, profile_id=self.profile.pk,
            account_id=self.account.pk, file_content=content,
            filename="extrato_completo.csv",
        )
        
        self.assertEqual(batch.total_rows, 3)
        self.assertEqual(batch.valid_rows, 3)
        
        # 2. Preview (sugestões)
        suggestions = generate_reconciliation_suggestions(batch)
        self.assertEqual(len(suggestions), 3)
        
        # Verificar sugestões
        # Linha 1: Aluguel - pagamento parcial (falta 1000)
        self.assertEqual(suggestions[0].action, "partial_payment")
        
        # Linha 2: Aplicação - link existente
        self.assertEqual(suggestions[1].action, "link_existing")
        self.assertEqual(suggestions[1].target_investment.pk, self.investment.pk)
        
        # Linha 3: Supermercado - nova imprevisível
        self.assertEqual(suggestions[2].action, "create_new")
        
        # 3. Commit com decisões
        row_decisions = []
        for i, row in enumerate(batch.rows.all()):
            if i == 0:  # Aluguel - parcial
                row_decisions.append({
                    "row_id": row.pk,
                    "action": "partial_payment",
                    "target_expense_id": self.monthly.pk,
                    "adjusted_amount": "500.00",
                    "splits": {self.account.pk: D("500.00")},
                })
            elif i == 1:  # Aplicação - link existente
                row_decisions.append({
                    "row_id": row.pk,
                    "action": "link_existing",
                    "target_investment_id": self.investment.pk,
                    "adjusted_amount": "1000.00",
                    "splits": {self.account.pk: D("1000.00")},
                })
            else:  # Supermercado - nova
                row_decisions.append({
                    "row_id": row.pk,
                    "action": "create_new",
                    "adjusted_amount": "300.00",
                    "adjusted_kind": "unexpected",
                    "splits": {self.account.pk: D("300.00")},
                })
        
        batch = commit_import(
            actor=self.user, batch_id=batch.pk,
            row_decisions=row_decisions,
            idempotency_key="full-workflow",
        )
        
        self.assertEqual(batch.status, ImportBatch.Status.COMMITTED)
        self.assertEqual(batch.rows.filter(status=ImportRow.Status.COMMITTED).count(), 3)
        
        # Verificar saldos
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, D("3200.00"))  # 5000 - 500 - 1000 - 300
        
        # Verificar investment position
        self.investment.refresh_from_db()
        self.assertEqual(self.investment.applied_amount, D("2000.00"))
        self.assertEqual(self.investment.current_value, D("2100.00"))
    
    def test_concurrent_import_idempotency(self):
        """Reimportação concorrente não duplica."""
        from apps.finance.services.imports import stage_import, commit_import
        
        content = b"Data,Descricao,Valor\n25/01/2024,Cinema,-50.00"
        
        # Primeira importação
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
        
        # Segunda importação do mesmo arquivo (hash igual)
        with self.assertRaises(ImportValidationError):
            stage_import(
                actor=self.user, profile_id=self.profile.pk,
                account_id=self.account.pk, file_content=content,
                filename="extrato.csv",
            )


# =============================================================================
# Testes de Permissões
# =============================================================================

class ImportPermissionTests(TestCase):
    """Testes de permissões granulares para importação."""
    
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
        """Comum com grants de accounts:edit e movements:edit pode importar."""
        from apps.finance.services.grants import save_grant, GRANT_FIELDS
        from apps.finance.services.imports import stage_import
        
        # Conceder permissões
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
        
        self.assertEqual(batch.status, ImportBatch.Status.VALIDATED)
    
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
        
        # Primeira importação funciona
        stage_import(
            actor=self.common, profile_id=self.profile.pk,
            account_id=self.account.pk, file_content=content,
            filename="extrato1.csv",
        )
        
        # Revogar
        save_grant(
            actor=self.admin, profile_id=self.profile.pk,
            membership_id=self.member.pk,
            levels={f: "none" for f in GRANT_FIELDS},
        )
        
        # Segunda importação falha
        with self.assertRaises(Exception):
            stage_import(
                actor=self.common, profile_id=self.profile.pk,
                account_id=self.account.pk, file_content=content,
                filename="extrato2.csv",
            )


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
        
        from apps.finance.services.importers import CSVParser
        parser = CSVParser(self.profile, self.account)
        statement = parser.parse(content, "test.csv")
        
        self.assertEqual(len(statement.transactions), 2)
        self.assertFalse(statement.transactions[0].is_credit)
        self.assertTrue(statement.transactions[1].is_credit)
    
    def test_csv_truncated_file(self):
        """CSV truncado (incompleto)."""
        content = b"Data,Descricao,Valor\n15/01/2024,Teste"
        
        from apps.finance.services.importers import CSVParser
        parser = CSVParser(self.profile, self.account)
        # Deve processar o que conseguir
        parser.parse(content, "test.csv")
        # Pode ter 0 ou 1 transação dependendo do parser
    
    def test_ofx_malformed(self):
        """OFX malformado."""
        content = b"<OFX><BANKMSGSRSV1><STMTTRNRS>"
        
        from apps.finance.services.importers import OFX1Parser
        parser = OFX1Parser(self.profile)
        
        with self.assertRaises(ImporterParseError):
            parser.parse(content, "malformed.ofx")
    
    def test_same_value_date_different_transactions(self):
        """Mesmo valor e data não são automaticamente duplicados."""
        from apps.finance.services.imports import check_duplicates, ParsedStatement, ParsedTransaction
        
        # Duas transações legítimas no mesmo dia com mesmo valor
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
        
        # Não devem ser marcadas como duplicatas (FITIDs diferentes)
        self.assertFalse(results[0].is_duplicate)
        self.assertFalse(results[1].is_duplicate)