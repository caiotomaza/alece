# SPDX-License-Identifier: GPL-3.0-only
"""Offline static contract; Django/PostgreSQL behavior needs separate integration tests."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_overview_no_longer_uses_profile_picker_for_income():
    view = (ROOT / 'src/controller/apps/finance/views.py').read_text()
    template = (ROOT / 'src/view/templates/finance/workspace_page.html').read_text()
    assert 'reverse("finance:income-bulk", args=[workspace_id])' in view
    assert 'data-income-dialog-trigger' in template
    assert 'id="overview-income-dialog"' in template


def test_server_side_single_transaction_and_privilege_checks():
    view = (ROOT / 'src/controller/apps/finance/views.py').read_text()
    part = view.split('def income_bulk_edit(',1)[1].split('\ndef record_config(',1)[0]
    for marker in ('transaction.atomic()', 'select_for_update()', 'user_can_module(',
                   'update_income(', 'profile_ids', 'status=409', 'status=422'):
        assert marker in part


def test_dialog_accessibility_and_nojs_fallback():
    template = (ROOT / 'src/view/templates/finance/_income_bulk_form.html').read_text()
    js = (ROOT / 'src/view/static/finance/alece_overview_income.js').read_text()
    assert '{% csrf_token %}' in template
    assert 'method="post"' in template
    assert 'data-income-cancel' in template and "href=" in template
    assert "dialog.showModal()" in js
    assert "confirmUnsaved" in js
    assert "credentials:'same-origin'" in js
    assert "form.getAttribute('action')" in js


def test_income_currency_uses_design_tokens_and_no_help_copy():
    html = (ROOT / 'src/view/templates/finance/_income_bulk_form.html').read_text()
    css = (ROOT / 'src/view/static/finance/alece_overview.css').read_text()
    assert '<span class="alece-income-currency" aria-hidden="true">R$</span>' in html
    assert 'alece-income-money' in html
    assert 'Deixe em branco se a renda for desconhecida' not in html
    assert 'alece-income-control input:focus-visible {outline:3px' not in css
    for token in ('--ds-size-control', '--ds-radius-control', '--ds-control-surface', '--ds-color-text'):
        assert token in css
    assert 'name="profile_ids"' in html
