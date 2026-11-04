# SPDX-License-Identifier: GPL-3.0-only
"""Proteções de saída e CSV. Testes sem dados reais."""
import csv
from datetime import date
from decimal import Decimal
from io import StringIO
from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.finance.services.reports import export_dre_csv, export_equity_csv


class SpreadsheetInjectionTests(SimpleTestCase):
    def test_dre_escapes_formula_in_profile_and_categories(self):
        report = SimpleNamespace(
            profile='=WEBSERVICE("https://invalid.example")',
            period_start=date(2026, 1, 1), period_end=date(2026, 1, 31),
            income_received=Decimal('12.00'), expenses_confirmed=Decimal('3.00'),
            net_result=Decimal('9.00'), income_by_type={'=1+2': Decimal('12.00')},
            expenses_by_type={'@CELL': Decimal('3.00')},
            expenses_by_category={'+1': Decimal('3.00')},
        )
        rows = list(csv.reader(StringIO(export_dre_csv(report).decode('utf-8-sig')), delimiter=';'))
        cells = [item for row in rows for item in row]
        for name in ('=WEBSERVICE(', '=1+2', '@CELL', '+1'):
            self.assertFalse(any(item.startswith(name) for item in cells))
        self.assertIn("'=1+2", cells)

    def test_equity_escapes_profile_formula(self):
        report = SimpleNamespace(profile='=1+1', period_start=date(2026, 1, 1), period_end=date(2026, 1, 31), points=[])
        rows = list(csv.reader(StringIO(export_equity_csv(report).decode('utf-8-sig')), delimiter=';'))
        self.assertIn("'=1+1", [cell for row in rows for cell in row])
