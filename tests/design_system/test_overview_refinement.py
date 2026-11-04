# SPDX-License-Identifier: GPL-3.0-only
"""Guards for the user-approved Overview refinement, without Django or a database."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
HTML = (ROOT / 'src/view/templates/finance/workspace_page.html').read_text(encoding='utf-8')
CSS = (ROOT / 'src/view/static/finance/alece_overview.css').read_text(encoding='utf-8')
OVERVIEW = HTML.split("{% if active_nav == 'overview' %}", 2)[-1].split("{% elif active_nav == 'expenses' %}")[0]


def test_single_neutral_empty_state_without_unrequested_action():
    assert OVERVIEW.count('O sistema não tem informações suficientes para gerar os dados.') == 1
    assert 'O planejamento ficará disponível' not in OVERVIEW
    assert 'Valores desconhecidos não são considerados zero.' not in OVERVIEW
    assert '>Informar renda</a>' not in OVERVIEW


def test_no_planning_edit_and_no_payment_note():
    assert 'Editar planejamento pela renda mensal' not in OVERVIEW
    assert 'Confirmar pagamento ou aplicação registra uma movimentação auditável.' not in OVERVIEW
    assert 'data-confirm-reversal' in OVERVIEW
    assert "finance:payment" in OVERVIEW


def test_outer_backdrop_removed_without_changing_theme_tokens():
    rule = CSS.split('.overview-home {', 1)[1].split('}', 1)[0]
    for expected in ('background: transparent;', 'border: 0;', 'padding: 0;'):
        assert expected in rule
    assert 'background: var(--surface);' in CSS
    assert '--ds-radius-card' in CSS


def test_equal_fixed_desktop_panels_with_internal_scrolling():
    block = CSS.split('.overview-home .overview-planning,', 1)[1].split('}', 1)[0]
    assert 'height: 490px;' in block
    assert 'overflow: hidden;' in block
    for selector in ('.overview-plan-scroll', '.overview-home #overview-month-card .month-table-wrap'):
        rule = CSS.split(selector + ' {', 1)[1].split('}', 1)[0]
        assert 'min-height: 0;' in rule
        assert 'overflow: auto;' in rule
        assert 'overscroll-behavior: contain;' in rule


def test_mobile_panels_use_adaptive_heights_and_month_scroll():
    assert '.overview-home .overview-planning {height: auto;' in CSS
    assert '.overview-home #overview-month-card {height: 400px;' in CSS
    assert 'min-width: 0; width: 100%; table-layout: fixed' in CSS
    assert 'min-width: 460px; table-layout: auto' in CSS
    assert 'position: sticky; top: 0;' in CSS
