/* ALECE accessibility progressive enhancement: no network calls or persistence. */
(() => {
  'use strict';
  const selectors = '.table-wrap, .settings-table-scroll, .month-table-wrap, .table-scroll, .perm-table-wrapper';
  let nextId = 0;
  function associateErrors(root = document) {
    root.querySelectorAll('form .field-group, form .form-group, form .settings-field').forEach(group => {
      const field = group.querySelector('input:not([type="hidden"]), select, textarea');
      if (!field) return;
      const errors = [...group.querySelectorAll('.errorlist, .settings-field-error, .message.error, .form-error')];
      if (!errors.length) return;
      field.setAttribute('aria-invalid', 'true');
      const tokens = new Set((field.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean));
      errors.forEach(error => {
        if (!error.id) error.id = 'alece-access-error-' + ++nextId;
        tokens.add(error.id);
      });
      field.setAttribute('aria-describedby', [...tokens].join(' '));
    });
  }
  function improveTables(root = document) {
    root.querySelectorAll(selectors).forEach(container => {
      const table = container.querySelector('table');
      if (!table) return;
      const overflowing = container.scrollWidth > container.clientWidth + 2;
      if (!overflowing) {
        if (container.dataset.aleceOverflow === 'true') {
          container.removeAttribute('tabindex'); container.removeAttribute('role');
          container.removeAttribute('aria-label'); delete container.dataset.aleceOverflow;
          container.parentElement?.querySelector(':scope > .alece-scroll-hint')?.remove();
        }
        return;
      }
      if (container.dataset.aleceOverflow === 'true') return;
      const heading = container.closest('section,article,.card,.page')?.querySelector('h1,h2,h3,h4');
      const caption = table.querySelector('caption');
      const name = caption?.textContent.trim() || heading?.textContent.trim() || 'Dados tabulares';
      container.dataset.aleceOverflow = 'true';
      container.tabIndex = 0;
      container.setAttribute('role','region');
      container.setAttribute('aria-label', 'Tabela rolável: ' + name);
      // Hint as visible text, not just a symbolic swipe gesture.
      const hint = document.createElement('p');
      hint.className = 'alece-scroll-hint';
      hint.textContent = 'Tabela extensa: deslize horizontalmente ou use as setas do teclado nesta região.';
      container.before(hint);
    });
  }
  function init() {associateErrors();improveTables();}
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, {once:true});
  else init();
  let resizeFrame = 0;
  window.addEventListener('resize', () => {
    if (resizeFrame) cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(() => {resizeFrame=0;improveTables();});
  });
  // Dialog contents are replaced dynamically. Do not poll, reattach listeners or submit forms.
  document.addEventListener('alece:dialog-content', event => associateErrors(event.target || document));
  window.AleceAccessibility = {associateErrors, improveTables};
})();
