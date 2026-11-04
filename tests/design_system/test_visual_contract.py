"""Teste real de CSS no Chromium; prévia isolada, não substitui testes Django."""
from pathlib import Path
import os
import pytest

ROOT = Path(__file__).resolve().parents[2]
CSS = ROOT / 'src/view/static/finance'
SAMPLE = ROOT / 'docs/design-system/exemplo-componentes.html'


@pytest.mark.browser
@pytest.mark.parametrize('theme', ('light', 'dark'))
@pytest.mark.parametrize('width,height', ((1280,900),(390,844)))
def test_responsive_theme_control_geometry_in_browser(theme, width, height):
    sync_api = pytest.importorskip('playwright.sync_api')
    executable = os.environ.get('ALECE_BROWSER_EXECUTABLE', '/usr/bin/chromium')
    if not Path(executable).exists():
        pytest.skip('Browser local não instalado; defina ALECE_BROWSER_EXECUTABLE')
    html = SAMPLE.read_text(encoding='utf-8')
    for name in ('alece_tokens.css','alece.css','alece_ui_consistency.css','alece_components.css'):
        html = html.replace(f'<link rel="stylesheet" href="../../src/view/static/finance/{name}">', '')
    with sync_api.sync_playwright() as p:
        browser = p.chromium.launch(executable_path=executable, headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':width, 'height':height})
        page.set_content(html)
        for name in ('alece_tokens.css','alece.css','alece_ui_consistency.css','alece_components.css'):
            page.add_style_tag(content=(CSS/name).read_text(encoding='utf-8'))
        page.locator('html').evaluate('(el,v)=>el.dataset.theme=v', theme)
        result = page.evaluate('''() => {
          const cs = s => {let e=document.querySelector(s);let c=getComputedStyle(e);return {h:Math.round(e.getBoundingClientRect().height),r:c.borderRadius,bgImage:c.backgroundImage,scheme:c.colorScheme};};
          return {button:cs('.preview-actions .button'),text:cs('.preview-fields input[type=text]'),select:cs('.preview-fields select'),filter:cs('.chart-category-form select'),checkbox:cs('.preview-chips input[type=checkbox]'),radio:cs('.preview-chips input[type=radio]'),overflow:document.documentElement.scrollWidth>innerWidth};
        }''')
        for key in ('button','text','select','filter'):
            assert result[key]['h'] == 44, (theme,width,key,result)
            assert result[key]['r'] == '12px', (theme,width,key,result)
        assert result['checkbox']['h'] == 20
        assert result['radio']['h'] == 20
        assert result['select']['bgImage'].startswith('url(')
        assert result['filter']['bgImage'].startswith('url(')
        assert not result['overflow']
        page.locator('.preview-fields input[type=text]').focus()
        assert page.locator('.preview-fields input[type=text]').evaluate('(el)=>getComputedStyle(el).outlineStyle') != 'none'
        browser.close()
