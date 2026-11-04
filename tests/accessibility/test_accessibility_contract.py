"""Browser/checks use OFFLINE static fixture; not Django/PostgreSQL or AT certification."""
from pathlib import Path
import re
import pytest
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / 'src/view/templates'
STATIC = ROOT / 'src/view/static/finance'
FIXTURE = ROOT / 'docs/acessibilidade/catalogo_teste.html'


def test_financial_tables_have_explicit_header_scope():
    for path in TEMPLATES.rglob('*.html'):
        html = path.read_text(encoding='utf-8')
        for header_group in re.findall(r'<thead\b[^>]*>.*?</thead>', html, re.S | re.I):
            assert not re.search(r'<th(?=[\s>])(?![^>]*\bscope=)', header_group, re.I), path


def test_alternative_chart_data_is_server_rendered_and_not_placeholder():
    dashboard = (TEMPLATES/'finance/reports_dashboard.html').read_text()
    history = (TEMPLATES/'finance/_history_chart.html').read_text()
    base = (TEMPLATES/'finance/base.html').read_text()
    assert 'Array(12).fill(0)' not in dashboard
    assert 'dashboard.equity.points %}' in dashboard
    assert 'dashboard.investments.positions %}' in dashboard
    assert '<details class="alece-chart-data">' in dashboard
    assert 'chart_series.points %}' in history
    assert '{% block extra_js %}' in base


def test_security_no_data_calls_in_accessibility_helper():
    helper = (STATIC/'alece_accessibility.js').read_text()
    assert 'fetch(' not in helper and 'localStorage' not in helper
    assert 'aria-describedby' in helper and 'aria-invalid' in helper


@pytest.mark.parametrize('width', [320,390,768,1280,1920])
@pytest.mark.parametrize('theme', ['light','dark'])
def test_layout_focus_table_error_and_theme_in_chromium(width,theme):
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':width,'height':840},reduced_motion='reduce')
        page.set_content(FIXTURE.read_text(encoding='utf-8'))
        for fname in ('alece_tokens.css','alece.css','alece_ui_consistency.css','alece_components.css','alece_modals.css','alece_accessibility.css'):
            page.add_style_tag(path=str(STATIC/fname))
        page.locator('html').evaluate('(el,theme)=>el.dataset.theme=theme',theme)
        page.add_script_tag(path=str(STATIC/'alece_accessibility.js'))
        assert page.locator('#demo-name').get_attribute('aria-invalid') == 'true'
        described_by = page.locator('#demo-name').get_attribute('aria-describedby')
        assert described_by
        assert page.locator('#'+described_by).inner_text() == 'Informe uma descrição válida.'
        page.locator('#demo-name').focus()
        outline=page.locator('#demo-name').evaluate('(el)=>getComputedStyle(el).outlineStyle')
        assert outline != 'none',(width,theme,outline)
        # The document must reflow; the financial table may scroll IN its region.
        x=page.evaluate('''() => ({doc:document.documentElement.scrollWidth,viewport:innerWidth,table:document.querySelector('.table-wrap'),
                     regions:[...document.querySelectorAll('[data-alece-overflow="true"]')].length})''')
        assert x['doc'] <= x['viewport']+1, (width,theme,x['doc'])
        if width <= 390:
            region=page.locator('.table-wrap').first
            assert region.get_attribute('role') == 'region'
            assert region.get_attribute('tabindex') == '0'
            assert page.get_by_text('Tabela extensa: deslize').count() > 0
        page.locator('.alece-chart-data summary').focus()
        assert page.locator('.alece-chart-data summary').evaluate('(el)=>getComputedStyle(el).outlineStyle') != 'none'
        # Verify the user can expand chart data without mouse.
        page.keyboard.press('Enter')
        expect(page.locator('.alece-chart-data')).to_have_attribute('open','')
        assert page.evaluate('matchMedia("(prefers-reduced-motion: reduce)").matches')
        page.close();browser.close()


def test_keyboard_skip_link_to_main():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':390,'height':800})
        page.set_content(FIXTURE.read_text())
        page.add_style_tag(path=str(STATIC/'alece.css'))
        page.keyboard.press('Tab')
        expect(page.locator('a.skip-link')).to_be_focused()
        page.keyboard.press('Enter')
        assert page.evaluate('location.hash')=='#main-content'
        browser.close()


def test_report_chart_javascript_executes_with_mocked_chart_data():
    """Browser-level JS smoke check only; values are synthetic and no Django views run."""
    template = (TEMPLATES/'finance/reports_dashboard.html').read_text()
    script = template.rsplit('<script>', 1)[-1].split('</script>',1)[0]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        page = browser.new_page()
        errors = []
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_content('''<html><body>
        <script id="alece-chart-equity" type="application/json">[{"date":"2026-10-01","net_equity":"150","bank_balance":"80","investment_value":"70"}]</script>
        <script id="alece-chart-investments" type="application/json">[{"name":"Exemplo","current_value":"70"}]</script>
        <canvas id="equityChart"></canvas><canvas id="investmentsChart"></canvas>
        </body></html>''')
        page.add_script_tag(path=str(ROOT/'src/view/static/vendor/chart.min.js'))
        page.add_script_tag(content=script)
        assert not errors,errors
        assert page.evaluate('Boolean(Chart.getChart("equityChart"))')
        assert page.evaluate('Boolean(Chart.getChart("investmentsChart"))')
        browser.close()
