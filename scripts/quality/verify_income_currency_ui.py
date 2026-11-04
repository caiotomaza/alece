# SPDX-License-Identifier: GPL-3.0-only
"""Visual-only smoke test: offline synthetic fixture, not Django integration."""
from pathlib import Path
import re
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[2]
fixture = root / 'tests/browser/fixtures/income_modal_preview.html'
html = fixture.read_text(encoding='utf-8')

def stylesheet(match):
    path = (fixture.parent / match.group(1)).resolve()
    if not path.is_relative_to(root):
        raise RuntimeError('Unsafe stylesheet path')
    return '<style>' + path.read_text(encoding='utf-8') + '</style>'

html = re.sub(r'<link rel="stylesheet" href="([^"]+)">', stylesheet, html)
html = re.sub(r'<script src="[^"]+" defer></script>', '', html)
passed = 0
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox'])
    for theme in ('light', 'dark'):
        for width in (320, 390, 768, 1280, 1920):
            page = browser.new_page(viewport={'width': width, 'height': 760}, device_scale_factor=1)
            page.set_content(html, wait_until='load')
            page.add_script_tag(path=str(root / 'src/view/static/finance/alece_modals.js'))
            page.add_script_tag(path=str(root / 'src/view/static/finance/alece_overview_income.js'))
            page.evaluate('(t) => document.documentElement.dataset.theme=t', theme)
            page.locator('[data-income-dialog-trigger]').click()
            assert page.get_by_role('dialog', name='Renda dos perfis financeiros').is_visible()
            assert page.locator('.alece-income-currency').all_text_contents() == ['R$', 'R$']
            assert page.get_by_text('Deixe em branco se a renda for desconhecida').count() == 0
            measure = page.evaluate('''() => ({
                pageOverflow: document.documentElement.scrollWidth > innerWidth + 1,
                modal: document.querySelector('.alece-income-dialog').getBoundingClientRect().height,
                input: document.querySelector('.alece-income-money input').getBoundingClientRect().height,
                focus: getComputedStyle(document.querySelector('.alece-income-money')).outlineStyle,
                outline: getComputedStyle(document.querySelector('.alece-income-money input')).outlineStyle,
                moneyOverflow: [...document.querySelectorAll('.alece-income-money')].some(el => el.scrollWidth > el.clientWidth + 1)
            })''')
            assert not measure['pageOverflow'] and not measure['moneyOverflow'], (theme, width, measure)
            assert measure['modal'] < 430 and measure['input'] >= 44, (theme, width, measure)
            assert measure['focus'] == 'none' and measure['outline'] == 'none', (theme, width, measure)
            page.keyboard.press('Tab')
            page.keyboard.press('Tab')
            focus_state = page.evaluate("""() => ({
                field: document.activeElement.name,
                outline: getComputedStyle(document.querySelector('.alece-income-money input')).outlineStyle,
            })""")
            assert focus_state == {'field':'income_1-monthly_income','outline':'solid'}, (theme,width,focus_state)
            assert page.locator('input[name="income_1-monthly_income"]').input_value() == '2.300,00'
            payload = page.locator('[data-income-bulk-form]').evaluate('(f) => new FormData(f).get("income_1-monthly_income")')
            assert payload == '2300.00', (theme, width, payload)
            print(f'OK: {theme} {width}px, R$ visual, campo intacto, modal responsivo, foco perceptível')
            passed += 1
            page.close()
    browser.close()
print(f'{passed} cenários isolados aprovados. Sem testes de integração Django/PostgreSQL.')
