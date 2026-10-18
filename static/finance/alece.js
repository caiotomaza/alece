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
})();
