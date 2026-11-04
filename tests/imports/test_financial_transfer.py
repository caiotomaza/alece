# SPDX-License-Identifier: GPL-3.0-only
"""Execute com Django e banco isolado: python manage.py test tests.imports.test_financial_transfer."""
from datetime import date
from decimal import Decimal
import hashlib
import io
import json
import zipfile

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.finance.models import (
    Workspace, WorkspaceMembership, FinancialProfile, ProfileGrant, BankAccount,
    RecurringExpense, UnexpectedExpense, TransactionBatch, LedgerLeg, JournalEntry,
    InvestmentPosition, ReservePolicy,
)
from apps.finance.services.financial_transfer import (
    MODEL_ORDER, export_payload, archive_bytes, parse_archive, import_payload,
)


class FinancialTransferTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='transfer-admin', password='safepass-4321')
        self.other = User.objects.create_user(username='transfer-common', password='safepass-4321')
        self.source = Workspace.objects.create(name='Origem', created_by=self.admin)
        self.target = Workspace.objects.create(name='Destino', created_by=self.admin)
        self.target_admin = WorkspaceMembership.objects.create(workspace=self.target, user=self.admin, role='admin')
        self.target_common = WorkspaceMembership.objects.create(workspace=self.target, user=self.other, role='common')
        WorkspaceMembership.objects.create(workspace=self.source, user=self.admin, role='admin')
        profile = FinancialProfile.objects.create(workspace=self.source, name='Principal', monthly_income=Decimal('3500.00'))
        self.profile = profile
        self.account = BankAccount.objects.create(profile=profile, name='Conta', kind='bank', opening_balance=Decimal('900'), balance=Decimal('850'))
        recurring = RecurringExpense.objects.create(profile=profile, name='Internet', category='essential', amount=Decimal('50'), due_day=10)
        TransactionBatch.objects.create(profile=profile, kind='income', amount=Decimal('50'), occurred_on=date(2026,10,1))
        batch = TransactionBatch.objects.create(profile=profile, kind='recurring', amount=Decimal('50'), occurred_on=date(2026,10,2), recurring_expense=recurring)
        LedgerLeg.objects.create(batch=batch, account=self.account, delta=Decimal('-50'))
        JournalEntry.objects.create(batch=batch, account_code='CUSTO', debit=Decimal('50'), credit=Decimal('0'))
        JournalEntry.objects.create(batch=batch, account_code='BANCO', debit=Decimal('0'), credit=Decimal('50'), bank_account=self.account)
        UnexpectedExpense.objects.create(profile=profile, name='Transporte', amount=Decimal('12'), recorded_on=date(2026,10,1))
        InvestmentPosition.objects.create(profile=profile, name='Reserva', category='reserve', current_value=Decimal('700'))
        ReservePolicy.objects.create(profile=profile, coverage_months=9)
        ProfileGrant.objects.create(membership=self.target_common, profile=FinancialProfile.objects.create(workspace=self.target,name='Existente'), overview_level='none')

    def test_archive_export_contains_only_financial_entities_and_xlsx(self):
        payload = export_payload(self.source.pk)
        self.assertEqual(set(payload['tables']), set(MODEL_ORDER))
        self.assertEqual(len(payload['tables']['FinancialProfile']), 1)
        raw = archive_bytes(payload)
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            self.assertIn('leitura_financeira.xlsx', z.namelist())
            self.assertIn('financeiro.json', z.namelist())
            data = z.read('financeiro.json').decode()
            self.assertNotIn('transfer-admin', data)
            self.assertNotIn('transfer-common', data)
            self.assertNotIn('ProfileGrant', data)
            self.assertNotIn('SystemLog', data)
            with zipfile.ZipFile(io.BytesIO(z.read('leitura_financeira.xlsx'))) as excel:
                self.assertIn('xl/workbook.xml', excel.namelist())
        self.assertEqual(parse_archive(raw)['tables'], payload['tables'])

    def test_import_remaps_links_preserves_old_profiles_and_rebuilds_access(self):
        payload = parse_archive(archive_bytes(export_payload(self.source.pk)))
        counts = import_payload(payload, workspace=self.target, actor=self.admin, grant_all_members=True)
        self.assertEqual(counts['FinancialProfile'], 1)
        dest = FinancialProfile.objects.get(workspace=self.target, name='Principal')
        self.assertNotEqual(dest.pk, self.profile.pk)
        self.assertEqual(dest.monthly_income, Decimal('3500.00'))
        account = BankAccount.objects.get(profile=dest, name='Conta')
        move = TransactionBatch.objects.get(profile=dest, kind='recurring')
        self.assertEqual(LedgerLeg.objects.get(batch=move).account_id, account.pk)
        self.assertEqual(JournalEntry.objects.filter(batch=move).count(), 2)
        grant = ProfileGrant.objects.get(profile=dest, membership=self.target_common)
        self.assertEqual(grant.expenses_level, 'edit')
        self.assertEqual(grant.movements_level, 'edit')
        self.assertEqual(ProfileGrant.objects.filter(profile=dest).count(), 2)
        self.assertTrue(FinancialProfile.objects.filter(workspace=self.target, name='Existente').exists())
        self.assertTrue(TransactionBatch.objects.filter(profile=self.profile).exists())

    def test_invalid_manifest_checksum_has_no_effect(self):
        blob = archive_bytes(export_payload(self.source.pk))
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            contents = {name:z.read(name) for name in z.namelist()}
        contents['financeiro.json'] += b' '
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
            for name, content in contents.items(): z.writestr(name, content)
        with self.assertRaises(ValidationError): parse_archive(buf.getvalue())
        self.assertEqual(FinancialProfile.objects.filter(workspace=self.target).count(), 1)

    def test_import_is_atomic_if_a_row_breaks_validation(self):
        payload = export_payload(self.source.pk)
        payload['tables']['RecurringExpense'][0]['amount'] = '-500'
        before = FinancialProfile.objects.filter(workspace=self.target).count()
        with self.assertRaises(ValidationError):
            import_payload(payload, workspace=self.target, actor=self.admin)
        self.assertEqual(FinancialProfile.objects.filter(workspace=self.target).count(), before)

    def test_non_admin_cannot_use_backup_endpoints(self):
        self.client.force_login(self.other)
        for route in ('financial-export', 'technical-reports'):
            response = self.client.get(reverse('finance:'+route, args=[self.target.pk]))
            self.assertEqual(response.status_code, 403)
        response = self.client.post(reverse('finance:financial-import', args=[self.target.pk]))
        self.assertEqual(response.status_code, 403)
