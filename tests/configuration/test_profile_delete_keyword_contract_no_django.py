# SPDX-License-Identifier: GPL-3.0-only
"""Contrato estático sem banco: proteção de exclusão exige palavra fixa no servidor.

Não substitui os testes Django de autorização, transações e preservação de dados.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "src/controller/apps/finance/services/profiles.py"
VIEW = ROOT / "src/controller/apps/finance/views.py"
TEMPLATE = ROOT / "src/view/templates/finance/profile_manage.html"


def test_service_verifies_uppercase_keyword_on_server():
    module = ast.parse(SERVICE.read_text(encoding="utf-8"))
    fn = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "delete_financial_profile")
    comparisons = [n for n in ast.walk(fn) if isinstance(n, ast.Compare)]
    assert any(
        isinstance(expr.left, ast.Name)
        and expr.left.id == "confirmation"
        and len(expr.ops) == 1
        and isinstance(expr.ops[0], ast.NotEq)
        and len(expr.comparators) == 1
        and isinstance(expr.comparators[0], ast.Constant)
        and expr.comparators[0].value == "CONFIRMAR"
        for expr in comparisons
    )


def test_view_only_reads_new_keyword_field():
    source = VIEW.read_text(encoding="utf-8")
    assert 'request.POST.get("confirm_deletion", "")' in source
    assert 'request.POST.get("confirm_profile_name"' not in source


def test_template_requires_keyword_and_disables_when_last_profile():
    source = TEMPLATE.read_text(encoding="utf-8")
    assert 'name="confirm_deletion"' in source
    assert 'pattern="CONFIRMAR"' in source
    assert 'Digite <strong>CONFIRMAR</strong>' in source
    assert 'name="confirm_profile_name"' not in source
    assert "{% if not can_remove_profile %}disabled{% endif %}" in source
    assert "{% csrf_token %}" in source
