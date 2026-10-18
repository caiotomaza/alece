/* Progressive enhancement only: financial writes always use Django forms. */
(() => {
  const root = document.documentElement;
  const toggle = document.querySelector('[data-theme-toggle]');
  let theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  try {
    const saved = localStorage.getItem('alece-theme');
    if (saved === 'light' || saved === 'dark') theme = saved;
  } catch (_) { /* The theme remains usable when storage is unavailable. */ }
  const applyTheme = () => {
    root.dataset.theme = theme;
    if (toggle) {
      toggle.hidden = false;
      toggle.setAttribute('aria-pressed', String(theme === 'dark'));
      toggle.setAttribute('aria-label', theme === 'dark' ? 'Ativar tema claro' : 'Ativar tema escuro');
      toggle.textContent = theme === 'dark' ? 'Claro' : 'Escuro';
    }
  };
  applyTheme();
  toggle?.addEventListener('click', () => {
    theme = theme === 'dark' ? 'light' : 'dark';
    applyTheme();
    try { localStorage.setItem('alece-theme', theme); } catch (_) { /* Optional preference. */ }
  });
  const dialog = document.querySelector('[data-edit-dialog]');
  const content = document.querySelector('[data-dialog-content]');
  if (dialog && content && typeof dialog.showModal === 'function') {
    const originalParent = content.parentNode;
    const originalNext = content.nextSibling;
    dialog.append(content);
    try {
      dialog.showModal();
      const invalid = dialog.querySelector('[aria-invalid="true"]');
      if (invalid) invalid.focus();
      dialog.addEventListener('cancel', (event) => {
        event.preventDefault();
        const cancel = dialog.querySelector('[data-dialog-cancel]');
        if (cancel) window.location.assign(cancel.href);
      });
    } catch (_) {
      originalParent.insertBefore(content, originalNext);
    }
  }
  document.querySelectorAll('[data-confirm-reversal]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      if (!window.confirm('Estornar a movimentação e preservar o histórico?')) event.preventDefault();
    });
  });
  const payment = document.querySelector('[data-payment-form]');
  if (payment) {
    const amount = payment.querySelector('[name="amount"]');
    const choices = [...payment.querySelectorAll('[name="accounts"]')];
    const selected = payment.querySelector('#selected-total');
    const gap = payment.querySelector('#payment-gap');
    const allocations = payment.querySelector('#account-allocations');
    const button = payment.querySelector('[type="submit"]');
    const toCents = (value) => {
      const clean = String(value || '').replace(',', '.');
      if (!/^\d+(\.\d{0,2})?$/.test(clean)) return NaN;
      const [whole, fraction = ''] = clean.split('.');
      return Number(whole) * 100 + Number(fraction.padEnd(2, '0'));
    };
    const display = (cents) => `R$ ${(cents / 100).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    const fullDue = toCents(payment.dataset.fullDue);
    const update = (auto) => {
      const requested = toCents(amount.value);
      let remaining = Number.isFinite(requested) ? requested : 0;
      let total = 0;
      allocations.replaceChildren();
      choices.filter((choice) => choice.checked).forEach((choice) => {
        const available = toCents(choice.dataset.balance);
        const used = Math.min(remaining, available);
        if (used > 0) {
          remaining -= used;
          total += used;
          const row = document.createElement('li');
          row.textContent = `${choice.parentElement.textContent.trim().split(' — ')[0]}: ${display(used)}`;
          allocations.append(row);
        }
      });
      selected.textContent = display(total);
      gap.textContent = Number.isFinite(requested) ? display(remaining) : '—';
      button.disabled = !Number.isFinite(requested) || requested <= 0 || remaining > 0;
      if (auto && !button.disabled && requested === fullDue) payment.requestSubmit();
    };
    amount.addEventListener('input', () => update(false));
    choices.forEach((choice) => choice.addEventListener('change', () => update(true)));
    update(false);
    payment.querySelector('[data-privacy-toggle]')?.addEventListener('click', (event) => {
      const hidden = payment.classList.toggle('is-private');
      event.currentTarget.setAttribute('aria-pressed', String(hidden));
      event.currentTarget.textContent = hidden ? 'Mostrar valores' : 'Ocultar valores';
    });
  }

  // Global "Ocultar valores" toggle (AT-155)
  const privacyToggle = document.querySelector('[data-privacy-toggle-global]');
  let isPrivate = localStorage.getItem('alece-privacy') === 'true';
  const applyPrivacy = () => {
    document.body.classList.toggle('is-private', isPrivate);
    if (privacyToggle) {
      privacyToggle.setAttribute('aria-pressed', String(isPrivate));
      privacyToggle.setAttribute('aria-label', isPrivate ? 'Mostrar valores' : 'Ocultar valores');
      privacyToggle.textContent = isPrivate ? 'Mostrar valores' : 'Ocultar valores';
      privacyToggle.setAttribute('aria-pressed', String(isPrivate));
    }
  };
  applyPrivacy();
  privacyToggle?.addEventListener('click', () => {
    isPrivate = !isPrivate;
    applyPrivacy();
    try { localStorage.setItem('alece-privacy', String(isPrivate)); } catch (_) {}
  });

  // Also apply to payment form toggle for consistency
  const paymentPrivacyToggle = document.querySelector('[data-privacy-toggle]');
  if (paymentPrivacyToggle) {
    paymentPrivacyToggle.addEventListener('click', (event) => {
      const hidden = payment.classList.toggle('is-private');
      event.currentTarget.setAttribute('aria-pressed', String(hidden));
      event.currentTarget.textContent = hidden ? 'Mostrar valores' : 'Ocultar valores';
    });
  }
})();
