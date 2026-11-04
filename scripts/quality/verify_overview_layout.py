from pathlib import Path
from playwright.sync_api import sync_playwright
from html import escape
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/visao-geral/evidencias'
OUT.mkdir(parents=True,exist_ok=True)
CSS=ROOT/'src/view/static/finance'
css='\n'.join((CSS/name).read_text() for name in ('alece_tokens.css','alece.css','alece_ui_consistency.css','alece_components.css','alece_modals.css','alece_accessibility.css','alece_overview.css'))
# CATALOGO SINTETICO: nao substitui o teste da aplicacao Django autenticada.
rows=[('Essenciais (Despesas)','40,0%','R$ 1.600,00'),('Estratégicas (Despesas)','12,5%','R$ 500,00'),('Discricionárias (Despesas)','10,0%','R$ 400,00'),('Imprevisíveis (Despesas)','0,0%','R$ 0,00'),('Desenvolvimento pessoal e profissional (Investimentos)','5,0%','R$ 200,00'),('Aquisição patrimonial (Investimentos)','10,0%','R$ 400,00'),('Consumo planejado (Investimentos)','5,0%','R$ 200,00'),('Reserva (Investimentos)','10,0%','R$ 400,00')]
rows_html=''.join(f'<tr><th scope="row"><span class="overview-plan-category"><span class="summary-swatch" style="background:{c}" aria-hidden="true"></span>{escape(n)}</span></th><td class="align-right">{p}</td><td class="align-right money">{v}</td></tr>' for (n,p,v),c in zip(rows,['#1A7F4B','#3D8E75','#C79A2B','#D65A4A','#3A7BC2','#6D59AF','#168C8F','#27694E']))
list_html=''.join(f'<li><span class="overview-plan-list-name"><span class="summary-swatch" style="background:{c}" aria-hidden="true"></span>{escape(n)}</span><span class="overview-plan-list-figures"><span>{p} da renda</span><strong class="money">{v}</strong></span></li>' for (n,p,v),c in zip(rows,['#1A7F4B','#3D8E75','#C79A2B','#D65A4A','#3A7BC2','#6D59AF','#168C8F','#27694E']))
css=css.replace('</style>','')
HTML='''<!doctype html><html lang="pt-BR" data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>'''+css+'''</style></head><body>
<div class="shell"><aside class="sidebar"><a class="brand" href="#"><span class="brandmark">A</span><span><strong>ALECE</strong><small>FINANCE</small></span></a><div class="nav-heading">Menu principal</div><nav class="nav-list"><a class="nav-button is-active" href="#">Visão geral</a><a class="nav-button" href="#">Despesas</a><a class="nav-button" href="#">Investimentos</a><a class="nav-button" href="#">Movimentações</a><a class="nav-button" href="#">Configurações</a></nav></aside><div class="main"><main class="content"><section class="page is-visible"><div class="intro"><div><h1>Visão geral</h1><p>Seu dinheiro, com mais clareza e controle.</p></div></div>
<div class="overview-home"><div class="overview-kpis">
<article class="card overview-kpi" aria-labelledby="overview-income-label"><div class="overview-kpi-copy"><h2 id="overview-income-label">Renda</h2><p>Mensal informada</p></div><div class="overview-kpi-value"><strong class="money">R$ 4.000,00</strong><a class="overview-kpi-action icon-button" href="#" aria-label="Editar renda mensal">✎</a></div></article>
<article class="card overview-kpi" aria-labelledby="overview-balance-label"><div class="overview-kpi-copy"><h2 id="overview-balance-label">Saldo</h2><p>Contas com valor conhecido</p></div><div class="overview-kpi-value"><strong class="money">R$ 7.250,00</strong><a class="overview-kpi-action icon-button" href="#" aria-label="Consultar contas e saldos do perfil">▤</a></div></article></div>
<div class="overview-main-grid"><article class="card overview-planning" id="overview-planning-card"><header class="overview-panel-header"><div><h2>Planejamento mensal</h2><p>Distribuição prevista da renda por categoria</p></div></header><div class="overview-plan-scroll" role="region" aria-label="Categorias do planejamento mensal"><table class="overview-plan-table"><thead><tr><th scope="col">Categoria</th><th scope="col" class="align-right">% da renda</th><th scope="col" class="align-right">Valor</th></tr></thead><tbody>'''+rows_html+'''</tbody></table></div><ul class="overview-plan-list">'''+list_html+'''</ul><footer class="overview-plan-footer"><span class="overview-plan-status"><strong>Alocado</strong> R$ 3.700,00</span><span class="overview-plan-status"><strong>Não alocado</strong> R$ 300,00</span></footer><p class="overview-panel-footnote">Valores estimados. Despesas previstas e aplicações sugeridas não significam pagamentos realizados.</p></article>
<article class="card" id="overview-month-card"><div class="panel-title"><div><h2>Este mês</h2><div class="muted panel-subtitle">Compromissos e aplicações sugeridas em 10/2026</div></div></div><div class="month-table-wrap" tabindex="0" role="region" aria-label="Compromissos e aplicações deste mês: tabela rolável"><table class="month-table"><thead><tr><th>Nome</th><th>Categoria</th><th>Vencimento</th><th class="align-right">Valor pendente</th><th>Pagar / aplicar</th></tr></thead><tbody><tr><td>Aluguel</td><td>Essenciais</td><td>10/10/2026</td><td class="align-right">R$ 1.200,00</td><td><a href="#">Confirmar</a></td></tr><tr><td>Internet</td><td>Essenciais</td><td>15/10/2026</td><td class="align-right">R$ 120,00</td><td><a href="#">Confirmar</a></td></tr></tbody></table></div></article></div>

</div></section></main></div></div></body></html>'''
# Stress-test dense data: enough rows to require internal scroll in the month card.
HTML = HTML.replace(
  '</tbody></table></div></article></div>',
  ('<tr><td>Despesa adicional com nome extenso</td><td>Essenciais</td><td>28/10/2026</td><td class="align-right money">R$ 250,00</td><td>Confirmar</td></tr>' * 28) + '</tbody></table></div></article></div>'
)
checks=[]
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox'])
 for theme in ('light','dark'):
  for width in (320,390,768,1280,1920):
   page=browser.new_page(viewport={'width':width,'height':900},device_scale_factor=1)
   page.set_content(HTML,wait_until='load')
   page.locator('html').evaluate('(node, theme) => node.setAttribute("data-theme",theme)',theme)
   page.wait_for_timeout(80)
   measured=page.evaluate('''() => {
      let cards=[...document.querySelectorAll('.overview-kpi,.overview-planning,#overview-month-card')];
      const planning=document.querySelector('.overview-planning');
      const month=document.querySelector('#overview-month-card');
      const scroll=document.querySelector('#overview-month-card .month-table-wrap');
      const backing=document.querySelector('.overview-home');
      return {viewport:innerWidth,document:document.documentElement.scrollWidth,
      planningHeight:Math.round(planning.getBoundingClientRect().height),monthHeight:Math.round(month.getBoundingClientRect().height),
      scrollOverflow:scroll.scrollHeight>scroll.clientHeight,backingBackground:getComputedStyle(backing).backgroundColor,
      backingBorder:getComputedStyle(backing).borderTopWidth,
      cardwidths:cards.map(e=>Math.round(e.getBoundingClientRect().width)),kpiColumns:getComputedStyle(document.querySelector('.overview-kpis')).gridTemplateColumns,mainColumns:getComputedStyle(document.querySelector('.overview-main-grid')).gridTemplateColumns,scrollContainer:document.querySelector('.overview-plan-scroll').scrollWidth>document.querySelector('.overview-plan-scroll').clientWidth};
   }''')
   assert measured['document']<=width+1, f'{theme}/{width} horizontal overflow: {measured}'
   assert all(w>140 for w in measured['cardwidths']),f'{theme}/{width} narrow cards: {measured}'
   assert page.get_by_role('heading',name='Planejamento mensal').count()==1
   assert page.get_by_role('heading',name='Este mês').count()==1
   if width >= 768:
    assert abs(measured['planningHeight'] - measured['monthHeight'])<=1, f'Panel heights diverged: {theme}/{width} {measured}'
   assert measured['scrollOverflow'], f'Month table failed to scroll internally: {theme}/{width} {measured}'
   assert measured['backingBorder']=='0px', f'Old backing border still visible: {theme}/{width} {measured}'
   if width in (320,1280):page.screenshot(path=str(OUT/f'refino_{theme}_{width}.png'),full_page=True)
   checks.append({'theme':theme,'width':width,**measured})
   page.close()
 browser.close()
(OUT/'resultado_viewports_refino.json').write_text(__import__('json').dumps({'note':'Catálogo estático com dados fictícios, não representa Django autenticado','checks':checks},ensure_ascii=False,indent=2))
for r in checks: print(f'{r["theme"]} {r["width"]}: sem overflow; colunas={r["kpiColumns"]} / {r["mainColumns"]}')
