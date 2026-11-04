/* ALECE - Modal and feedback primitives. Dependency-free progressive enhancement.
 * Without JavaScript Django links/forms remain normal pages and POST requests.
 */
(() => {
  'use strict';
  let serial = 0;
  const toText = (value) => String(value == null ? '' : value);
  const focusStart = (dialog, preferred) => {
    const target = preferred || dialog.querySelector('[autofocus], [aria-invalid="true"], [data-initial-focus], button, input:not([type="hidden"]), select, textarea, a[href]');
    if (target) target.focus({preventScroll: true});
  };
  const labelDialog = (dialog) => {
    const heading = dialog.querySelector('[data-dialog-content] .dialog-title h2, [data-dialog-content] h2, [data-dialog-content] h1')
      || dialog.querySelector('.dialog-title h2, h2, h1');
    if (heading) {
      if (!heading.id) heading.id = 'alece-dialog-title-' + ++serial;
      dialog.setAttribute('aria-labelledby', heading.id);
      dialog.removeAttribute('aria-label');
    } else {
      dialog.removeAttribute('aria-labelledby');
      dialog.setAttribute('aria-label', 'Janela de edição');
    }
  };
  const linkErrors = (scope = document) => {
    scope.querySelectorAll('form').forEach((form) => {
      form.querySelectorAll('.field-group, .permission-levels label').forEach((group) => {
        const field = group.querySelector('input:not([type="hidden"]), select, textarea');
        const errors = [...group.querySelectorAll('.errorlist, .settings-field-error, .message.error')];
        if (!field || !errors.length) return;
        field.setAttribute('aria-invalid', 'true');
        for (const error of errors) {
          if (!error.id) error.id = 'alece-field-error-' + ++serial;
          const ids = new Set((field.getAttribute('aria-describedby') || '').split(/\s+/).filter(Boolean));
          ids.add(error.id);
          field.setAttribute('aria-describedby', [...ids].join(' '));
        }
      });
    });
  };
  const notify = (message, state = 'error', scope = document) => {
    let target = scope.querySelector('[data-operation-feedback]');
    if (!target) {
      target = document.createElement('p');
      target.dataset.operationFeedback = '';
      target.className = 'alece-operation-feedback';
      const content = scope.querySelector('[data-dialog-content]') || scope.querySelector('form') || document.querySelector('main, .content') || document.body;
      const heading = content.querySelector('.dialog-title');
      if (heading) heading.insertAdjacentElement('afterend', target);
      else content.prepend(target);
    }
    target.dataset.state = state;
    target.setAttribute('role', state === 'error' || state === 'conflict' || state === 'forbidden' ? 'alert' : 'status');
    target.textContent = toText(message);
    return target;
  };
  const confirm = ({title = 'Confirmar operação', message = '', confirmLabel = 'Confirmar', destructive = false, cancelLabel = 'Cancelar'} = {}) => new Promise((resolve) => {
    if (typeof HTMLDialogElement === 'undefined' || !HTMLDialogElement.prototype.showModal) {
      // Without native modal support, preserve the underlying server-side action.
      resolve(false);
      return;
    }
    const dialog = document.createElement('dialog');
    dialog.className = 'alece-confirm-dialog';
    const id = 'alece-confirm-title-' + ++serial;
    dialog.setAttribute('aria-labelledby', id);
    const body = document.createElement('div');
    body.className = 'alece-confirm-content';
    const heading = document.createElement('h2');
    heading.id = id; heading.textContent = title; heading.tabIndex = -1;
    const description = document.createElement('p');
    description.textContent = message;
    const footer = document.createElement('footer');
    footer.className = 'alece-confirm-actions';
    const cancel = document.createElement('button');
    cancel.type = 'button'; cancel.className = 'button secondary'; cancel.textContent = cancelLabel;
    const accept = document.createElement('button');
    accept.type = 'button'; accept.className = destructive ? 'button danger' : 'button';
    accept.textContent = confirmLabel;
    footer.append(cancel, accept); body.append(heading, description, footer); dialog.append(body);
    document.body.append(dialog);
    let result = false;
    cancel.addEventListener('click', () => dialog.close());
    accept.addEventListener('click', () => { result = true; dialog.close(); });
    dialog.addEventListener('click', (event) => { if (event.target === dialog) dialog.close(); });
    dialog.addEventListener('close', () => { dialog.remove(); resolve(result); }, {once:true});
    dialog.showModal();
    // Least destructive option receives focus on potentially destructive operations.
    (destructive ? cancel : heading).focus({preventScroll:true});
  });
  const confirmUnsaved = ({canSave = false, reason = ''} = {}) => new Promise((resolve) => {
    const dialog = document.createElement('dialog');
    dialog.className = 'alece-confirm-dialog alece-unsaved-confirm-dialog';
    const title = document.createElement('h2');
    title.id = 'alece-unsaved-title-' + ++serial;
    title.textContent = 'Alterações não salvas'; title.tabIndex = -1;
    dialog.setAttribute('aria-labelledby', title.id);
    const body = document.createElement('div'); body.className = 'alece-confirm-content';
    const note = document.createElement('p');
    note.textContent = canSave ? 'Deseja salvar este formulário antes de fechar?' :
      reason || 'Existem alterações em mais de um formulário ou uma operação sensível. Salve cada formulário separadamente.';
    const footer = document.createElement('footer'); footer.className = 'alece-confirm-actions';
    const keep = document.createElement('button');
    keep.type = 'button'; keep.className = 'button secondary'; keep.textContent = 'Continuar editando';
    const discard = document.createElement('button');
    discard.type = 'button'; discard.className = 'button danger secondary'; discard.textContent = 'Descartar';
    footer.append(keep, discard);
    if (canSave) {
      const save = document.createElement('button'); save.type = 'button'; save.className = 'button'; save.textContent = 'Salvar';
      footer.append(save); save.addEventListener('click', () => {choice = 'save'; dialog.close();});
    }
    body.append(title, note, footer); dialog.append(body); document.body.append(dialog);
    let choice = 'continue';
    keep.addEventListener('click', () => dialog.close());
    discard.addEventListener('click', () => {choice = 'discard'; dialog.close();});
    dialog.addEventListener('click', (event) => {if (event.target === dialog) dialog.close();});
    dialog.addEventListener('close', () => {dialog.remove(); resolve(choice);}, {once:true});
    dialog.showModal(); keep.focus({preventScroll:true});
  });
  // Capture-phase confirmation applies to normal server forms and dynamically fetched forms.
  // A one-time WeakSet token avoids re-confirming the exact same requestSubmit action.
  const approved = new WeakSet();
  document.addEventListener('submit', async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.hasAttribute('data-alece-confirm')) return;
    if (typeof HTMLDialogElement === 'undefined' || !HTMLDialogElement.prototype.showModal) return;
    if (approved.has(form)) { approved.delete(form); return; }
    event.preventDefault(); event.stopImmediatePropagation();
    const button = event.submitter;
    const accepted = await confirm({
      title: form.dataset.confirmTitle || 'Confirmar operação',
      message: form.dataset.aleceConfirm,
      confirmLabel: form.dataset.confirmLabel || 'Confirmar',
      destructive: form.dataset.confirmDestructive !== 'false',
    });
    if (!accepted || !form.isConnected) return;
    approved.add(form);
    try { form.requestSubmit(button && button.isConnected ? button : undefined); }
    finally { approved.delete(form); }
  }, true);
  // Chromium may momentarily focus <body> when Tab wraps in a native dialog.
  // Explicit boundary handling keeps keyboard focus in the topmost open dialog.
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Tab' || event.defaultPrevented) return;
    const dialogs = [...document.querySelectorAll('dialog[open]')];
    const top = dialogs.at(-1);
    if (!top) return;
    const items = [...top.querySelectorAll('a[href],button:not([disabled]),input:not([type="hidden"]):not([disabled]),select:not([disabled]),textarea:not([disabled]),summary,[tabindex]:not([tabindex="-1"])')]
      .filter((el) => !el.closest('[hidden]') && el.getClientRects().length && el.tabIndex >= 0);
    if (!items.length) {event.preventDefault();top.focus();return;}
    const active = document.activeElement;
    if (!top.contains(active)) {event.preventDefault();(event.shiftKey ? items.at(-1) : items[0]).focus();return;}
    if (event.shiftKey && active === items[0]) {event.preventDefault();items.at(-1).focus();}
    if (!event.shiftKey && active === items.at(-1)) {event.preventDefault();items[0].focus();}
  }, true);
  document.addEventListener('DOMContentLoaded', () => linkErrors());
  window.AleceModal = Object.freeze({confirm, confirmUnsaved, notify, linkErrors, focusStart, labelDialog});
})();
