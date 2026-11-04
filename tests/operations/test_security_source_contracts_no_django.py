# SPDX-License-Identifier: GPL-3.0-only
"""Exercita rotinas puras de segurança sem instalar Django; não substitui integração DB."""
import ast
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import os
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def extract_functions(source_path, names, namespace):
    parsed = ast.parse((ROOT / source_path).read_text(encoding="utf-8"))
    functions = [node for node in parsed.body if isinstance(node, ast.FunctionDef) and node.name in names]
    if len(functions) != len(names):
        raise AssertionError("Não foi possível localizar as funções exigidas no código real.")
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(source_path), "exec"), namespace)
    return namespace


class SecuritySourceContracts(unittest.TestCase):
    def test_report_csv_does_not_execute_formula_looking_profile_or_categories(self):
        ns = extract_functions("src/controller/apps/finance/services/reports.py",
            {"_csv_text", "export_dre_csv", "export_equity_csv"},
            {"DREReport": object, "EquityEvolutionReport": object})
        report = SimpleNamespace(profile="=HYPERLINK(\"https://invalid.example\")",
            period_start=date(2026,1,1), period_end=date(2026,1,31),
            income_received=Decimal("42.00"), expenses_confirmed=Decimal("2.00"),
            net_result=Decimal("40.00"), income_by_type={"+1+2":Decimal(42)},
            expenses_by_type={"@function":Decimal(2)},
            expenses_by_category={"=7+3":Decimal(2)})
        raw = ns["export_dre_csv"](report).decode("utf-8-sig")
        self.assertIn("'=HYPERLINK", raw)
        self.assertIn("'+1+2", raw)
        self.assertIn("'@function", raw)
        self.assertIn("'=7+3", raw)
        self.assertNotIn(";=HYPERLINK", raw)

    def _credential_functions(self, folder):
        class FakeImproperlyConfigured(Exception):
            pass
        env = {"Path":Path, "os":os, "tempfile":tempfile, "SECRET_DIR":folder,
               "ImproperlyConfigured":FakeImproperlyConfigured}
        return extract_functions("src/controller/apps/core/ai_credentials.py",
            {"_path", "read_token", "write_token", "has_token", "delete_token"}, env)

    def test_provider_token_rotation_and_revoke(self):
        with TemporaryDirectory() as d:
            fn = self._credential_functions(Path(d) / "private")
            fn["write_token"](4, "FIRST-EXAMPLE")
            fn["write_token"](4, "SECOND-EXAMPLE")
            self.assertEqual(fn["read_token"](4), "SECOND-EXAMPLE")
            self.assertEqual((Path(d)/"private"/"provider-4.key").stat().st_mode & 0o777, 0o600)
            self.assertTrue(fn["delete_token"](4))
            self.assertFalse(fn["delete_token"](4))
            self.assertFalse(fn["has_token"](4))

    def test_provider_token_revoke_refuses_symlink(self):
        with TemporaryDirectory() as d:
            folder = Path(d) / "private"
            folder.mkdir()
            dest = Path(d) / "original"
            dest.write_text("EXAMPLE_ONLY")
            (folder/"provider-4.key").symlink_to(dest)
            fn = self._credential_functions(folder)
            with self.assertRaises(fn["ImproperlyConfigured"]):
                fn["delete_token"](4)
            self.assertEqual(dest.read_text(), "EXAMPLE_ONLY")

    def test_sensitive_forms_have_django_exception_redaction(self):
        source = (ROOT / "src/controller/apps/core/user_views.py").read_text()
        self.assertIn('@sensitive_post_parameters("new_password1", "new_password2")',source)
        self.assertIn('@sensitive_post_parameters("password1", "password2")',source)
        self.assertIn('revoke_db_sessions_for_user(target_user.pk)',source)

    def test_no_plaintext_sql_like_session_revocation(self):
        source = (ROOT / "src/controller/apps/core/user_views.py").read_text()
        self.assertNotIn("session_data__contains", source)
        self.assertIn("revoke_db_sessions_for_user", source)
        self.assertIn("get_decoded()", (ROOT / "src/controller/apps/core/session_security.py").read_text())

    def test_report_cache_has_no_store_and_safe_name(self):
        source = (ROOT / "src/controller/apps/finance/reports_views.py").read_text()
        self.assertIn('response["Cache-Control"] = "private, no-store, max-age=0"', source)
        self.assertIn('filename = f"{report_type}_perfil-{profile.pk}', source)


if __name__ == "__main__":
    unittest.main()
