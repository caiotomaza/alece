# SPDX-License-Identifier: GPL-3.0-only
"""Regression guards for the redesigned ALECE investments screen."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT / 'src/view/templates/finance/workspace_page.html'
GOALS = ROOT / 'src/view/templates/finance/_goal_panel.html'
SUGGESTIONS = ROOT / 'src/view/templates/finance/investment_suggestions.html'
CSS = ROOT / 'src/view/static/finance/alece.css'
METRICS = ROOT / 'src/controller/apps/finance/services/metrics.py'
OBJECT_FORM = ROOT / 'src/view/templates/finance/object_form.html'
VIEWS = ROOT / 'src/controller/apps/finance/views.py'


def test_investments_page_uses_wireframe_panel_and_registered_positions_table():
    html = WORKSPACE.read_text(encoding='utf-8')
    assert "{% include 'finance/_goal_panel.html' %}" in html
    assert 'Investimentos cadastrados' in html
    assert 'Posições financeiras' in html
    assert 'Adicionar investimento' in html
    assert '{% if not investment_count %}<tr><td colspan="7">Nenhuma posição financeira cadastrada.</td></tr>{% endif %}' in html


def test_goal_panel_renders_cards_support_metrics_and_ctas():
    html = GOALS.read_text(encoding='utf-8')
    for token in (
        'investment-wireframe-panel',
        'investment-goal-grid',
        'investment-goal-card',
        'investment-goal-ring',
        'investment-support-grid',
        'Registrar meta / posição',
        'Configurar reserva',
        'Meta da Reserva = todas as despesas previsíveis + média mensal das imprevisíveis',
    ):
        assert token in html, token
    assert '{{ action_urls.investment }}' in html
    assert "{% url 'finance:reserve-edit' section.profile.pk %}" in html
    assert '{{ section.summary.coverage_months }} meses de proteção' in html


def test_suggestion_table_stays_in_pt_br_and_explains_popup_profile_selection():
    html = SUGGESTIONS.read_text(encoding='utf-8')
    for token in ('Objetivo', 'Valor atual', 'Meta', 'Falta', 'Sugestão mensal', 'Prazo estimado'):
        assert token in html
    assert 'perfil financeiro é selecionado no próprio pop-up' in html.lower()
    assert 'source-table' in html


def test_metrics_expose_progress_and_gap_for_visual_cards():
    text = METRICS.read_text(encoding='utf-8')
    for token in ('"progress_pct": progress_pct', '"gap": gap', 'target_value = targets[category]'):
        assert token in text


def test_css_contains_new_investments_layout_and_responsive_rules():
    css = CSS.read_text(encoding='utf-8')
    for token in (
        '.investment-wireframe-panel',
        '.investment-goal-grid',
        '.investment-goal-ring',
        '.investment-support-grid',
        '.investment-suggestion-panel',
        '@media(max-width:1180px)',
        '@media(max-width:760px)',
    ):
        assert token in css, token


def test_popup_form_contract_remains_the_same_for_profile_selection():
    html = OBJECT_FORM.read_text(encoding='utf-8')
    views = VIEWS.read_text(encoding='utf-8')
    assert 'Preencha os dados e confirme o perfil financeiro deste registro.' in html
    assert 'profile_id' in views
    assert 'ModelChoiceField' in views
    assert 'Escolher o destino não altera a preferência de navegação da sessão.' in views


def test_runtime_release_marker_and_locale_safe_donut_progress():
    html = GOALS.read_text(encoding='utf-8')
    css = CSS.read_text(encoding='utf-8')
    assert 'data-alece-investments-ui="wireframe-r2-20261104"' in html
    assert '{% load l10n %}' in html
    assert '{{ category.progress_pct|unlocalize }}' in html
    assert '--goal-progress:' in html
    assert '--goal-progress' in css
    assert '<details class="investment-planning-details">' in html
    assert '<summary>Ver detalhes do planejamento financeiro</summary>' in html
    assert '.investment-goal-card.is-development{--goal-accent:var(--ds-color-brand)}' in css
    assert '.investment-goal-card.is-reserve{--goal-accent:var(--ds-color-success)}' in css
    assert 'Despesas essenciais mensais' not in html
    assert 'Meta da Reserva = todas as despesas previsíveis' in html
