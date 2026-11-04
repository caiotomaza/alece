# SPDX-License-Identifier: GPL-3.0-only
"""Proteções verificáveis sem Django/PostgreSQL; não substituem testes HTTP."""
import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _real_redactor():
    source = ROOT / "src/controller/apps/core/views.py"
    root = ast.parse(source.read_text(encoding="utf-8"))
    functions = [node for node in root.body if isinstance(node, ast.FunctionDef)
                 and node.name == "_safe_diagnostic_line"]
    if len(functions) != 1:
        raise AssertionError("Função de sanitização ausente")
    namespace = {"re": re}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), "exec"), namespace)
    return namespace["_safe_diagnostic_line"]


class PrivacySourceTests(unittest.TestCase):
    def test_sensitive_diagnostic_lines_are_entirely_suppressed(self):
        sanitize = _real_redactor()
        for entry in (
            'api_token="secret-with spaces"',
            '{"access_token": "credential with space"}',
            'GET /callback?refresh_token=abc&amount=987.65',
            'POST password = password_example',
            'headers: Authorization: Bearer token-example',
            'x-api-key=temporary-secret',
            'cookie: sessionid=abc',
            'DATABASE_URL=postgres://username:password@server/db',
        ):
            with self.subTest(entry=entry[:18]):
                output = sanitize(entry)
                self.assertTrue(output.startswith("[REDACTED:"), output)
                self.assertNotIn("credential", output)
                self.assertNotIn("987.65", output)
        self.assertEqual(sanitize("HTTP 503 | incidente=ABC123"), "HTTP 503 | incidente=ABC123")

    def test_dashboard_uses_escaped_json_script_not_safe_or_python_repr(self):
        template = (ROOT / "src/view/templates/finance/reports_dashboard.html").read_text()
        self.assertIn('chart_investments|json_script:"alece-chart-investments"', template)
        self.assertIn('chart_equity|json_script:"alece-chart-equity"', template)
        self.assertIn("JSON.parse(document.getElementById", template)
        self.assertNotIn("dashboard.investments|safe", template)
        self.assertNotIn("dashboard.equity|safe", template)
        view = (ROOT / "src/controller/apps/finance/reports_views.py").read_text()
        self.assertIn('"chart_investments": chart_investments', view)
        self.assertIn('"chart_equity": chart_equity', view)
        self.assertNotIn("{{ field.help_text|safe }}", (ROOT / "src/view/templates/finance/object_form.html").read_text())
