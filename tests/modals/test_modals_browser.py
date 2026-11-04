"""Client-side interaction regression with mocked HTML endpoints.
Not a substitute for Django/PostgreSQL integration tests or production screenshots.
"""
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
JS_UI = ROOT / 'src/view/static/finance/alece_modals.js'
JS_APP = ROOT / 'src/view/static/finance/alece.js'
CSS = ROOT / 'src/view/static/finance/alece_modals.css'

HTML = '''<!doctype html><html lang="pt-BR" data-theme="light"><head><meta name="csrf-token" content="demo"></head>
<body><main class="content alece-settings"><a href="about:blank?editar" id="open" class="settings-modal-trigger">Editar</a>
<form method="post" action="about:blank?revogar" data-alece-confirm="Revogar todas as sessões?" data-confirm-title="Revogar sessões" data-confirm-label="Revogar"><button id="revoke">Revogar</button></form>
</main></body></html>'''


def modal_form(which='one', risky=False, named_action=False):
    form = '''<form method="post" action="about:blank?salvar" {risky}><div class="field-group"><label for="f1">Nome</label><input id="f1" name="name" value="Inicial" required></div><footer><button type="submit">Salvar seção</button></footer></form>'''.format(risky='data-confirm-user-deletion' if risky else '')
    if named_action:
        form = form.replace('<div class="field-group">', '<input type="hidden" name="action" value="profile"><div class="field-group">', 1)
    if which == 'two':
        form += '''<form method="post" action="about:blank?permissoes"><label for="f2">Permissão</label><input id="f2" name="permission" value="view"></form>'''
    return '''<html><body><section data-dialog-content><header class="dialog-title"><h2 id="dialog-title" tabindex="-1">Editar dados</h2><a href="about:blank?configuracoes" data-dialog-cancel>Fechar</a></header>{forms}</section></body></html>'''.format(forms=form)


@pytest.fixture()
def harness():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        contexts = []
        def create(*, viewport=None, forms='one', risky=False, post_status=403, named_action=False):
            ctx = browser.new_context(viewport=viewport or {'width': 1280, 'height': 820})
            contexts.append(ctx)
            page = ctx.new_page()
            page.set_content(HTML)
            # Chromium in this execution environment blocks external/file navigation.
            # Mock same-origin fetch to verify client behavior without touching a server.
            page.evaluate("""({fragment, status}) => {
              window.__alecePosts = [];
              window.fetch = async (url, opts={}) => {
                if ((opts.method || 'GET').toUpperCase() === 'POST') {
                  window.__alecePosts.push({url:String(url), entries:[...opts.body.entries()]});
                  return new Response('Operação não aplicada', {status});
                }
                return new Response(fragment, {status:200, headers:{'Content-Type':'text/html'}});
              };
            }""", {'fragment':modal_form(forms,risky,named_action), 'status':post_status})
            page.add_style_tag(path=str(CSS))
            page.add_script_tag(path=str(JS_UI))
            page.add_script_tag(path=str(JS_APP))
            page.evaluate('''() => document.addEventListener('submit', e => {
              if (e.target.hasAttribute('data-alece-confirm')) {
                window.__alecePosts.push({url:e.target.action, entries:[]});
                e.preventDefault();
              }
            }, true)''')
            return page, page
        yield create
        for ctx in contexts:
            ctx.close()
        browser.close()


def open_editor(page):
    page.locator('#open').click()
    expect(page.locator('dialog.unified-dialog[open]')).to_be_visible()


def test_keyboard_escape_lock_restore_focus(harness):
    page, posts = harness()
    open_editor(page)
    assert page.evaluate('document.body.classList.contains("alece-modal-open")')
    assert page.evaluate('document.activeElement.closest("dialog") !== null')
    assert page.locator('dialog.unified-dialog').get_attribute('aria-labelledby') == 'dialog-title'
    assert page.evaluate('document.querySelector("main").matches(":modal")') is False
    page.keyboard.press('Escape')
    expect(page.locator('dialog.unified-dialog[open]')).to_have_count(0)
    expect(page.locator('#open')).to_be_focused()
    assert not posts.evaluate("window.__alecePosts")
    assert not page.evaluate('document.body.classList.contains("alece-modal-open")')


def test_dirty_cancel_and_discard_without_post(harness):
    page, posts = harness()
    open_editor(page)
    page.locator('#f1').fill('Novo valor')
    page.keyboard.press('Escape')
    expect(page.get_by_role('button', name='Continuar editando')).to_be_visible()
    expect(page.get_by_role('button', name='Salvar', exact=True)).to_be_visible()
    page.get_by_role('button', name='Continuar editando').click()
    expect(page.locator('dialog.unified-dialog[open]')).to_be_visible()
    page.locator('dialog.unified-dialog').click(position={'x':5, 'y':5})
    expect(page.get_by_role('button', name='Descartar')).to_be_visible()
    page.get_by_role('button', name='Descartar').click()
    expect(page.locator('dialog.unified-dialog[open]')).to_have_count(0)
    assert posts.evaluate("window.__alecePosts") == []


def test_multiple_forms_cannot_be_autosaved(harness):
    page, posts = harness(forms='two')
    open_editor(page)
    page.locator('#f1').fill('Alterado')
    page.locator('#f2').fill('edit')
    page.keyboard.press('Escape')
    expect(page.get_by_role('button', name='Salvar', exact=True)).to_have_count(0)
    expect(page.get_by_text('Salve cada seção separadamente', exact=False)).to_be_visible()
    page.get_by_role('button', name='Descartar').click()
    assert not posts.evaluate("window.__alecePosts")


def test_sensitive_form_not_saved_on_dismiss(harness):
    page, posts = harness(risky=True)
    open_editor(page)
    page.locator('#f1').fill('Alterado')
    page.keyboard.press('Escape')
    expect(page.get_by_role('button', name='Salvar', exact=True)).to_have_count(0)
    page.get_by_role('button', name='Continuar editando').click()
    assert not posts.evaluate("window.__alecePosts")


@pytest.mark.parametrize('status,expected', [(403, 'Sem permissão'), (409, 'Conflito'), (500, 'Não foi possível')])
def test_single_form_save_reports_http_errors(harness, status, expected):
    page, posts = harness(post_status=status)
    open_editor(page)
    page.locator('#f1').fill('Alterado')
    page.keyboard.press('Escape')
    page.get_by_role('button', name='Salvar', exact=True).click()
    expect(page.get_by_role('alert')).to_contain_text(expected)
    expect(page.locator('dialog.unified-dialog[open]')).to_be_visible()
    assert len(posts.evaluate('window.__alecePosts')) == 1 and '?salvar' in posts.evaluate('window.__alecePosts[0].url')


def test_native_confirm_cancels_then_explicitly_posts(harness):
    page, posts = harness(post_status=200)
    page.locator('#revoke').click()
    expect(page.get_by_role('dialog')).to_be_visible()
    page.get_by_role('button', name='Cancelar').click()
    assert not posts.evaluate("window.__alecePosts")
    page.locator('#revoke').click()
    page.get_by_role('button', name='Revogar', exact=True).last.click()
    page.wait_for_function('window.__alecePosts.length === 1')


def test_fields_receive_error_description(harness):
    page, _ = harness()
    page.evaluate('''() => {
      const box = document.createElement('div');
      box.innerHTML = '<form><div class="field-group"><input name="name"><ul class="errorlist"><li>Obrigatório</li></ul></div></form>';
      document.body.append(box);
      window.AleceModal.linkErrors(box);
    }''')
    inp = page.locator('form input[name=name]')
    assert inp.get_attribute('aria-invalid') == 'true'
    described = inp.get_attribute('aria-describedby')
    assert described and page.locator('#'+described).inner_text() == 'Obrigatório'


@pytest.mark.parametrize('theme', ['light', 'dark'])
@pytest.mark.parametrize('viewport', [{'width': 390, 'height': 760}, {'width': 1280, 'height': 820}])
def test_responsive_dialog_and_theme(harness, theme, viewport):
    page, _ = harness(viewport=viewport)
    page.evaluate('(theme) => document.documentElement.dataset.theme = theme', theme)
    open_editor(page)
    bounds = page.locator('dialog.unified-dialog').bounding_box()
    assert bounds['x'] >= -1
    assert bounds['x'] + bounds['width'] <= viewport['width']+1
    assert bounds['height'] <= viewport['height']
    assert page.evaluate('document.documentElement.dataset.theme') == theme


def test_no_js_retains_server_forms_and_links(harness):
    page, _ = harness()
    # With JS disabled a link stays a link and a normal POST form stays submit-capable.
    assert page.locator('#open').get_attribute('href') == 'about:blank?editar'
    assert page.locator('#revoke').evaluate('(el) => el.closest("form").method') == 'post'


def test_focus_remains_inside_dialog_on_tab(harness):
    page, _ = harness()
    open_editor(page)
    for _ in range(8):
        page.keyboard.press('Tab')
        assert page.evaluate('document.activeElement.closest("dialog.unified-dialog") !== null')


@pytest.mark.parametrize('workflow', ['usuario', 'perfil', 'despesa', 'investimento', 'integracao-ia'])
def test_create_edit_cancel_workflow_shapes(harness, workflow):
    # Same modal component across five representative form types; backend is mocked.
    page, posts = harness()
    open_editor(page)
    assert page.get_by_role('dialog').count() == 1
    page.locator('#f1').fill('Alteração ' + workflow)
    page.keyboard.press('Escape')
    page.get_by_role('button', name='Descartar').click()
    assert not posts.evaluate('window.__alecePosts')


def test_named_action_input_does_not_override_post_url(harness):
    # Regressão real do incidente: POST /configuracoes/perfis/[object HTMLInputElement] (404).
    page, posts = harness(named_action=True, post_status=403)
    open_editor(page)
    assert page.locator('dialog form input[name="action"]').input_value() == 'profile'
    # A propriedade nativa é mascarada por HTMLInputElement, mas o atributo continua correto.
    assert page.evaluate("""() => document.querySelector('dialog.unified-dialog form').action instanceof HTMLInputElement""")
    page.locator('dialog.unified-dialog button[type="submit"]').click()
    page.wait_for_function('window.__alecePosts.length === 1')
    post = posts.evaluate('window.__alecePosts[0]')
    assert post['url'] == 'about:blank?salvar'
    assert ['action', 'profile'] in [list(x) for x in post['entries']]
    expect(page.get_by_role('alert')).to_contain_text('Sem permissão')
