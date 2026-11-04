# SPDX-License-Identifier: GPL-3.0-only
"""Offline synthetic Chromium test, NOT a Django/PostgreSQL integration test."""
from pathlib import Path
import re
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
fixture = ROOT / 'tests/browser/fixtures/income_modal_preview.html'
html = fixture.read_text()
def css_inline(m):
    path = (fixture.parent / m.group(1)).resolve()
    assert path.is_relative_to(ROOT)
    return '<style>' + path.read_text() + '</style>'
html = re.sub(r'<link rel="stylesheet" href="([^"]+)">', css_inline, html)
html = re.sub(r'<script src="[^"]+" defer></script>', '', html)
output = ROOT / 'docs/visao-geral/evidencias'
output.mkdir(parents=True, exist_ok=True)
passed = 0
with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox'])
    for theme in ('light', 'dark'):
        for width in (320,390,768,1280,1920):
            page = browser.new_page(viewport={'width':width,'height':800}, device_scale_factor=1)
            page.set_content(html,wait_until='load')
            page.add_script_tag(path=str(ROOT/'src/view/static/finance/alece_modals.js'))
            page.add_script_tag(path=str(ROOT/'src/view/static/finance/alece_overview_income.js'))
            page.evaluate('(t)=>document.documentElement.dataset.theme=t',theme)
            page.locator('[data-income-dialog-trigger]').click()
            dlg = page.get_by_role('dialog', name='Renda dos perfis financeiros')
            assert dlg.is_visible()
            assert dlg.locator('.alece-income-close').is_visible()
            assert page.locator('.alece-income-currency').all_text_contents() == ['R$','R$']
            assert page.locator('.alece-income-help').count() == 0
            assert page.locator('input[name="income_1-monthly_income"]').input_value() == '2.300,00'
            assert page.evaluate('document.activeElement.id') == 'income-modal-title'
            page.keyboard.press('Tab')
            assert page.evaluate('document.activeElement.hasAttribute("data-income-close")')
            page.keyboard.press('Tab')
            assert page.evaluate('document.activeElement.name') == 'income_1-monthly_income'
            assert page.locator('.alece-income-money input').first.evaluate('(el)=>getComputedStyle(el).outlineStyle') == 'solid' 
            sizes = dlg.evaluate('''el => ({
                height:el.getBoundingClientRect().height,
                viewport:innerHeight,
                documentOverflow:document.documentElement.scrollWidth>innerWidth+1,
                bodyOverflow:document.body.scrollWidth>innerWidth+1,
                inputHeights:[...el.querySelectorAll('.alece-income-money input')].map(i=>i.getBoundingClientRect().height),
                fieldsOverlap:[...el.querySelectorAll('.alece-income-money')].some(x=>x.scrollWidth>x.clientWidth+1)
            })''')
            assert not sizes['documentOverflow'] and not sizes['bodyOverflow'] and not sizes['fieldsOverlap'],(theme,width,sizes)
            assert sizes['height'] <= min(430,sizes['viewport']-20),(theme,width,sizes)
            assert all(h >= 43 for h in sizes['inputHeights']), (theme,width,sizes)
            assert dlg.get_by_role('button',name='Salvar').is_visible()
            if width in (390,1280):
                page.screenshot(path=str(output/f'renda_redesign_{theme}_{width}.png'),full_page=True)
            field=page.locator('input[name="income_1-monthly_income"]')
            field.fill('1.500,50')
            field.press('Tab')
            assert field.input_value() == '1.500,50'
            canonical = page.locator('[data-income-bulk-form]').evaluate('f=>new FormData(f).get("income_1-monthly_income")')
            assert canonical == '1500.50',(theme,width,canonical)
            page.get_by_role('button',name='Salvar').click()
            # Without remote server the UI may show a synthetic connection error, but no navigation is allowed.
            assert dlg.is_visible()
            passed += 1
            page.close()
    browser.close()
print(f'APROVADO: {passed} combinações isoladas, temas e larguras, formato BRL/POST, sem dados reais.')
