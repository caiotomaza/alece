/* SPDX-License-Identifier: GPL-3.0-only */
/* Income popup: one atomic Django form, no profile-picker step or forced navigation. */
(() => {
  'use strict';
  const dialog = document.getElementById('overview-income-dialog');
  const trigger = document.querySelector('[data-income-dialog-trigger]');
  if (!dialog || !trigger || typeof dialog.showModal !== 'function') return;
  const form = dialog.querySelector('[data-income-bulk-form]');
  const message = dialog.querySelector('[data-income-message]');
  const save = dialog.querySelector('[data-income-save]');
  const closeButton = dialog.querySelector('[data-income-close]');
  if (closeButton) closeButton.hidden = false;
  const moneyInputs = Array.from(form.querySelectorAll('.alece-income-money input'));
  const canonicalMoney = (value) => {
    const raw = value.trim();
    if (!raw) return '';
    if (/^\d+(?:\.\d{1,2})?$/.test(raw)) return raw;
    if (/^\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?$/.test(raw)) return raw.replace(/\./g, '').replace(',', '.');
    if (/^\d+(?:,\d{1,2})?$/.test(raw)) return raw.replace(',', '.');
    return null; // Mantém o valor inválido para o Django apresentar erro de validação.
  };
  const formatMoney = (field) => {
    const canonical = canonicalMoney(field.value);
    if (canonical === null || canonical === '') return;
    const number = Number(canonical);
    if (Number.isFinite(number)) {
      field.value = new Intl.NumberFormat('pt-BR', {minimumFractionDigits:2, maximumFractionDigits:2}).format(number);
    }
  };
  moneyInputs.forEach((field) => field.addEventListener('blur', () => formatMoney(field)));
  // FormData é usado tanto pelo fetch quanto por submissões nativas.
  form.addEventListener('formdata', (event) => {
    for (const field of moneyInputs) {
      const canonical = canonicalMoney(field.value);
      if (canonical !== null) event.formData.set(field.name, canonical);
    }
  });
  let baseline = '';
  let submitting = false;
  let dismissing = false;
  const snapshot = () => new URLSearchParams(new FormData(form)).toString();
  const showError = (text) => {message.textContent = text; message.hidden = false;};
  const clearErrors = () => {
    message.textContent = ''; message.hidden = true;
    dialog.querySelectorAll('[data-income-error-for]').forEach((node) => {node.textContent = '';});
    form.querySelectorAll('[aria-invalid="true"]').forEach((node) => {
      node.removeAttribute('aria-invalid');node.removeAttribute('aria-describedby');
    });
  };
  const closeDialog = () => {dialog.close();};
  const requestDismiss = async () => {
    if (submitting || dismissing) return;
    if (snapshot() === baseline) {closeDialog();return;}
    dismissing = true;
    try {
      const result = await window.AleceModal.confirmUnsaved({canSave:true});
      if (result === 'discard') {form.reset();clearErrors();closeDialog();}
      if (result === 'save') form.requestSubmit();
    } finally {dismissing = false;}
  };
  trigger.addEventListener('click', (event) => {
    if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    clearErrors();
    moneyInputs.forEach(formatMoney);
    baseline = snapshot();
    dialog.showModal();
    document.documentElement.classList.add('alece-income-modal-open');
    document.body.classList.add('alece-income-modal-open');
    // Foco inicial no título: nenhum campo aparece indevidamente em estado de edição.
    dialog.querySelector('.alece-income-title').focus({preventScroll:true});
  });
  dialog.addEventListener('cancel', (event) => {event.preventDefault(); void requestDismiss();});
  dialog.addEventListener('click', (event) => {
    if (event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) void requestDismiss();
  });
  dialog.querySelectorAll('[data-income-cancel], [data-income-close]').forEach((control) => {
    control.addEventListener('click', (event) => {
      event.preventDefault();void requestDismiss();
    });
  });
  dialog.addEventListener('close', () => {
    document.documentElement.classList.remove('alece-income-modal-open');
    document.body.classList.remove('alece-income-modal-open');
    trigger.focus({preventScroll:true});
  });
  form.addEventListener('submit', async (event) => {
    if (submitting) {event.preventDefault();return;}
    if (!window.fetch) return; // Normal server-side POST remains functional.
    event.preventDefault();
    clearErrors();
    submitting = true;save.disabled=true;form.setAttribute('aria-busy','true');
    try {
      const response = await fetch(form.getAttribute('action'), {
        method:'POST',credentials:'same-origin',headers:{'Accept':'application/json'},body:new FormData(form),
      });
      const contentType = response.headers.get('content-type') || '';
      if (!contentType.includes('application/json')) {
        if (response.redirected) {window.location.assign(response.url);return;}
        showError(response.status === 403 ? 'Você não tem permissão para editar estas rendas.' :
          'A sessão pode ter expirado. Atualize a página e tente novamente.');return;
      }
      const result = await response.json();
      if (response.ok && result.ok) {window.location.reload();return;}
      showError(result.message || (response.status === 403 ? 'Sem permissão para editar esta renda.' : 'Não foi possível salvar os valores.'));
      const errors = result.field_errors || {};
      for (const [fieldName, texts] of Object.entries(errors)) {
        const field = form.elements.namedItem(fieldName);
        const error = [...dialog.querySelectorAll('[data-income-error-for]')].find(node => node.dataset.incomeErrorFor === fieldName);
        if (!field || !error) continue;
        error.textContent = texts.join(' ');
        field.setAttribute('aria-invalid','true');
        field.setAttribute('aria-describedby',error.id);
      }
      (form.querySelector('[aria-invalid="true"]') || message).focus?.({preventScroll:true});
    } catch (_) {showError('Erro de conexão. Nenhum salvamento foi confirmado.');}
    finally {submitting=false;save.disabled=false;form.removeAttribute('aria-busy');}
  });
})();
