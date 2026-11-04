# SPDX-License-Identifier: GPL-3.0-only
"""Layout-only regression guards, independent of Django/PostgreSQL."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "src/view/templates/finance/workspace_page.html"
CSS = ROOT / "src/view/static/finance/alece_overview.css"
METRICS = ROOT / "src/controller/apps/finance/services/metrics.py"


def test_overview_follows_wireframe_hierarchy_and_preserves_navigation():
    html = TEMPLATE.read_text(encoding="utf-8")
    for name in ('overview-kpis', 'overview-main-grid', 'overview-planning',
                 'overview-month-card'):
        assert name in html
    positions = [html.index('class="overview-kpis"'),
                 html.index('class="overview-main-grid"'),
                 html.index('id="overview-planning-card"'),
                 html.index('id="overview-month-card"')]
    assert positions == sorted(positions)
    assert html.count('data-confirm-reversal') == 1
    for url in ('finance:reverse-item', 'finance:payment', 'finance:profile-detail'):
        assert url in html
    assert "{% elif active_nav == 'expenses' %}" in html
    assert "{% elif active_nav == 'investments' %}" in html


def test_overview_renders_only_positive_categories_without_faking_income():
    html = TEMPLATE.read_text(encoding="utf-8")
    metrics = METRICS.read_text(encoding="utf-8")
    assert html.count('for category in income_plan.categories') == 2
    assert 'income_plan.all_categories' not in html
    assert '{% if income_plan.categories %}' in html
    assert 'Nenhuma categoria com valor acima de zero neste planejamento.' in html
    assert '"all_categories": all_categories' in metrics
    assert '"source": source, "percent": percent' in metrics
    assert 'if value <= ZERO:' in metrics
    assert '{% if income_plan %}' in html
    assert 'O sistema não tem informações suficientes para gerar os dados.' in html
    assert 'income_plan.allocated' in html
    assert 'income_plan.unallocated' in html


def test_overview_monthly_kind_labels_are_pt_br_and_internal_codes_stay_stable():
    import ast

    html = TEMPLATE.read_text(encoding="utf-8")
    views = ROOT / "src/controller/apps/finance/views.py"
    tree = ast.parse(views.read_text(encoding="utf-8"))
    mapping = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "MONTHLY_ITEM_LABELS"
                for target in node.targets)
    )
    assert mapping == {
        "recurring": "Previsível",
        "unexpected": "Imprevisível",
        "application": "Aplicação",
    }
    assert 'row["kind_label"] = MONTHLY_ITEM_LABELS.get(' in views.read_text(encoding="utf-8")
    assert '{{ item.kind_label }}' in html
    assert '{{ item.kind }}' not in html
    assert "section.profile.pk item.kind item.object.pk" in html


def test_theme_responsiveness_accessibility_and_progressive_enhancement():
    html = TEMPLATE.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    assert 'alece_overview.css' in html
    for token in ('var(--surface)', 'var(--surface-alt)', 'var(--text)', 'var(--border)'):
        assert token in css
    for key in ('max-width: 760px', 'max-width: 540px'):
        assert key in css
    assert 'prefers-reduced-motion' in (ROOT / 'src/view/static/finance/alece_accessibility.css').read_text(encoding='utf-8')
    assert 'role="region" aria-label="Compromissos' in html
    assert '<th scope="row">' in html
    assert '<th scope="col">' in html
    assert 'tabindex="0"' in html
    assert 'data-overview-expand' not in html
    assert 'overview-details' not in html
    assert 'overview-summary-card' not in html
    assert 'overview-accounts-card' not in html
    assert 'alece_overview.js' not in html
    assert '!important' not in css


def test_css_parses():
    import tinycss2
    css = CSS.read_text(encoding="utf-8")
    errors = [t for t in tinycss2.parse_stylesheet(css, skip_whitespace=True,
                skip_comments=True) if t.type == "error"]
    assert not errors, errors


def test_removed_details_does_not_leave_dead_balance_link_or_change_financial_actions():
    html = TEMPLATE.read_text(encoding="utf-8")
    assert 'Ver contas, investimentos e distribuição detalhada' not in html
    assert '<details class="overview-details"' not in html
    assert 'href="#overview-details"' not in html
    assert "{% url 'finance:profile-detail' sections.0.profile.pk %}" in html
    assert 'sections.0.can_accounts_view' in html
    assert html.count('id="overview-income-label"') == 1
    assert html.count('id="overview-balance-label"') == 1
    for token in ('overview-planning-card', 'overview-month-card', 'data-confirm-reversal', 'csrf_token'):
        assert token in html, token
