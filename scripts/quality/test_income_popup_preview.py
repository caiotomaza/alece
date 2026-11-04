from pathlib import Path
import re
import json
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[2]
html=(root/'tests/browser/fixtures/income_modal_preview.html').read_text()
def css_replace(match):
    path=match.group(1)
    target=(root/'tests/browser/fixtures'/path).resolve()
    return '<style>'+target.read_text()+'</style>'
html=re.sub(r'<link rel="stylesheet" href="([^"]+)">',css_replace,html)
html=re.sub(r'<script src="[^"]+" defer></script>', '', html)
results=[]
with sync_playwright() as playwright:
 browser=playwright.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 for theme,width in [('light',1280),('dark',390)]:
  page=browser.new_page(viewport={'width':width,'height':760},device_scale_factor=1)
  page.set_content(html, wait_until='load')
  page.add_script_tag(path=str(root/'src/view/static/finance/alece_modals.js'))
  page.add_script_tag(path=str(root/'src/view/static/finance/alece_overview_income.js'))
  page.evaluate('(theme)=>document.documentElement.dataset.theme=theme',theme)
  page.locator('[data-income-dialog-trigger]').click()
  assert page.locator('#overview-income-dialog').evaluate('(el)=>el.open')
  assert page.get_by_role('dialog',name='Renda dos perfis financeiros').count()==1
  assert page.evaluate('document.body.classList.contains("alece-income-modal-open")')
  assert page.evaluate('document.activeElement.id') == 'income-modal-title'
  assert page.locator('.alece-income-currency').count()==2
  assert all(text=='R$' for text in page.locator('.alece-income-currency').all_text_contents())
  assert page.locator('.alece-income-help').count()==0
  assert page.locator('.alece-income-dialog').evaluate('(el)=>el.getBoundingClientRect().height') < 430
  assert page.locator('.alece-income-money input').first.evaluate('(el)=>getComputedStyle(el).borderRadius') == '12px'
  assert page.locator('[name="income_1-monthly_income"]').input_value() == '2.300,00'
  assert page.locator('.alece-income-money').first.evaluate('(el)=>getComputedStyle(el).outlineStyle') == 'none'
  out=root/f'docs/visao-geral/evidencias/renda_redesign_{theme}_{width}.png'
  page.screenshot(path=str(out),full_page=True)
  results.append(f'{theme}/{width}: modal sobre Visão geral, foco e scroll OK')
  if theme=='light':
   page.locator('[name="income_1-monthly_income"]').fill('2500')
   page.get_by_role('link',name='Cancelar').click()
   assert page.get_by_role('heading',name='Alterações não salvas').is_visible()
   page.get_by_role('button',name='Continuar editando').click()
   assert page.locator('#overview-income-dialog').evaluate('(el)=>el.open')
   page.get_by_role('link',name='Cancelar').click()
   page.get_by_role('button',name='Descartar').click()
   page.wait_for_function('!document.getElementById("overview-income-dialog").open')
   assert page.locator('[data-income-dialog-trigger]').evaluate('(el)=>el===document.activeElement')
   results.append('cancelar/descartar/continuar e restauracao de foco OK')
   page.locator('[data-income-dialog-trigger]').click()
   def handler(route):
    route.fulfill(status=422,content_type='application/json',body=json.dumps({
     'ok':False,'message':'Revise os valores informados.',
     'field_errors':{'income_2-monthly_income':['Valor invalido.']}
    }))
   page.evaluate('''window.fetch=async()=>({ok:false,status:422,redirected:false,headers:{get:()=>"application/json"},json:async()=>({ok:false,message:"Revise os valores informados.",field_errors:{"income_2-monthly_income":["Valor invalido."]}})});''')
   page.locator('[data-income-save]').click()
   page.get_by_text('Valor invalido.').wait_for()
   assert page.locator('[name="income_2-monthly_income"]').get_attribute('aria-invalid')=='true'
   assert page.locator('#overview-income-dialog').evaluate('(el)=>el.open')
   results.append('HTTP 422: erro vinculado ao campo, modal mantido aberto OK')
  page.close()
 browser.close()

print('\n'.join(results))
