/* Progressive enhancement only: financial writes always use Django forms. */
(() => {
  const root = document.documentElement;
  const toggles = document.querySelectorAll('[data-theme-toggle]');
  const userId = root.dataset.userId || '';
  const cacheKey = userId ? `alece-theme-user-${userId}` : 'alece-theme-anonymous';
  // The first paint already uses the server-rendered DB preference; synchronize the cache.
  let theme = root.dataset.theme === 'dark' ? 'dark' : 'light';
  try { localStorage.setItem(cacheKey, theme); } catch (_) { /* Private browsing. */ }
  const applyTheme = () => {
    root.dataset.theme = theme;
    toggles.forEach((toggle) => {
      toggle.hidden = false;
      toggle.setAttribute('aria-pressed', String(theme === 'dark'));
      toggle.setAttribute('aria-label', theme === 'dark' ? 'Ativar tema claro' : 'Ativar tema escuro');
      toggle.title = theme === 'dark' ? 'Ativar tema claro' : 'Ativar tema escuro';
      const icon = toggle.querySelector('use');
      if (icon) icon.setAttribute('href', theme === 'dark' ? '#i-moon' : '#i-sun');
      else toggle.textContent = theme === 'dark' ? 'Claro' : 'Escuro';
    });
  };
  applyTheme();
  let savingTheme = false;
  toggles.forEach((toggle) => toggle.addEventListener('click', async () => {
    if (savingTheme) return;
    const previous = theme;
    theme = previous === 'dark' ? 'light' : 'dark';
    applyTheme();
    savingTheme = true;
    try {
      const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
      const response = await fetch(root.dataset.themeEndpoint || '/preferencias/tema/', {
        method: 'POST', credentials: 'same-origin',
        headers: {'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': csrf},
        body: new URLSearchParams({theme}),
      });
      if (!response.ok) throw new Error('Falha ao salvar preferência');
      const saved = await response.json();
      if (saved.theme !== theme) throw new Error('Resposta inesperada');
      try { localStorage.setItem(cacheKey, theme); } catch (_) { /* Optional. */ }
    } catch (error) {
      theme = previous;
      applyTheme();
      // Never imply that an unsaved preference will synchronize to other devices.
      window.AleceModal?.notify('Não foi possível salvar o tema no servidor. Tente novamente.');
    } finally {
      savingTheme = false;
    }
  }));
  // Todos os pop-ups compartilham lock de scroll e verificação de alterações não salvas.
  // Nenhuma exclusão, revogação, pagamento ou redefinição é salva ao fechar por engano.
  const modalOriginalScroll = {top: 0, active: false};
  const hasOpenDialogs = () => Boolean(document.querySelector('dialog[open]'));
  const syncModalScroll = () => {
    if (hasOpenDialogs() && !modalOriginalScroll.active) {
      modalOriginalScroll.top = window.scrollY;
      modalOriginalScroll.active = true;
      document.documentElement.classList.add('alece-modal-open');
      document.body.classList.add('alece-modal-open');
      document.body.style.top = `-${modalOriginalScroll.top}px`;
    } else if (!hasOpenDialogs() && modalOriginalScroll.active) {
      document.body.style.top = '';
      document.documentElement.classList.remove('alece-modal-open');
      document.body.classList.remove('alece-modal-open');
      modalOriginalScroll.active = false;
      window.scrollTo(0, modalOriginalScroll.top);
    }
  };
  const fieldFingerprint = (form) => JSON.stringify(
    [...new FormData(form)].map(([name, value]) =>
      [name, value instanceof File ? [value.name, value.size, value.lastModified] : value]));
  const tracked = new WeakMap();
  const snapshotForms = (scope) => scope.querySelectorAll('form').forEach((form) => {
    tracked.set(form, fieldFingerprint(form));
  });
  const isChanged = (form) => tracked.has(form) && fieldFingerprint(form) !== tracked.get(form);
  const isRisky = (form) => form.matches(
    '[data-destructive-action], [data-confirm-profile-deletion], [data-confirm-user-deletion], [data-confirm-user-removal]')
    || Boolean(form.querySelector('input[type="password"]'))
    || Boolean(form.querySelector('[name="action"][value="toggle_archive"]'));

  // Nunca salvar vários formulários em sequência: cada POST tem escopo próprio.
  // Salvar pelo fechamento é permitido somente para um formulário não sensível.
  const attachModalBehavior = (dialog, afterClose) => {
    const requestDismiss = async () => {
      if (dialog.dataset.dismissBusy === '1') return;
      dialog.dataset.dismissBusy = '1';
      try {
        const changed = [...dialog.querySelectorAll('form')].filter(isChanged);
        if (!changed.length) {dialog.close(); return;}
        const safeSingleForm = changed.length === 1 && !isRisky(changed[0]);
        const choice = await window.AleceModal.confirmUnsaved({
          canSave: safeSingleForm,
          reason: changed.length > 1 ? 'Há mais de um formulário alterado. Salve cada seção separadamente ou descarte as alterações.' :
            'Esta operação é sensível. Use o botão específico para confirmar, ou descarte as alterações.'
        });
        if (choice === 'discard') dialog.close();
        if (choice === 'save' && safeSingleForm) {
          const form = changed[0];
          if (form.reportValidity()) {
            // requestSubmit respeita validação nativa, CSRF e o backend existente.
            // Não executa requisições concorrentes nem presume sucesso.
            form.requestSubmit();
          } else window.AleceModal.notify('Revise os campos indicados antes de salvar.', 'error', dialog);
        }
      } finally {
        dialog.dataset.dismissBusy = '0';
      }
    };
    dialog.addEventListener('cancel', (event) => {event.preventDefault(); void requestDismiss();});
    dialog.addEventListener('click', (event) => {
      if (event.target === dialog) void requestDismiss();
      const cancel = event.target.closest?.('[data-dialog-cancel]');
      if (cancel && dialog.contains(cancel)) {event.preventDefault(); void requestDismiss();}
    });
    dialog.addEventListener('close', () => {
      syncModalScroll();
      if (afterClose === 'navigate') window.location.assign(dialog.querySelector('[data-dialog-cancel]')?.href || '/configuracoes/');
    });
    return requestDismiss;
  };

  const dialog = document.querySelector('[data-edit-dialog]');
  const content = document.querySelector('[data-dialog-content]');
  if (dialog && content && typeof dialog.showModal === 'function') {
    const originalParent = content.parentNode;
    const originalNext = content.nextSibling;
    if (content.contains(dialog)) document.body.append(dialog);
    dialog.append(content);
    try {
      attachModalBehavior(dialog, 'navigate');
      snapshotForms(dialog);
      dialog.showModal();
      syncModalScroll();
      window.AleceModal.linkErrors(dialog);
      window.AleceModal.labelDialog(dialog);
      window.AleceModal.focusStart(dialog, dialog.querySelector('[aria-invalid="true"]'));
    } catch (_) {
      originalParent.insertBefore(content, originalNext);
      syncModalScroll();
    }
  }
  // Open server-rendered forms over the current page; without JS, links still work.
  if (typeof HTMLDialogElement !== 'undefined' && typeof HTMLDialogElement.prototype.showModal === 'function') {
    let overlay;
    let opening = false;
    let activeTrigger;
    document.addEventListener('click', async (event) => {
      const link = event.target.closest('a.account-add-btn, a.account-edit-btn, a.alece-edit-action, a.balances-new-account, a.settings-modal-trigger');
      if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const url = new URL(link.href, window.location.href);
      if (url.origin !== window.location.origin || opening) return;
      event.preventDefault();
      opening = true;
      try {
        const response = await fetch(url, {credentials: 'same-origin', headers: {'X-Requested-With': 'XMLHttpRequest'}});
        if (!response.ok) throw new Error('Form unavailable');
        const page = new DOMParser().parseFromString(await response.text(), 'text/html');
        const formContent = page.querySelector('[data-dialog-content]');
        if (!formContent) throw new Error('No dialog content');
        activeTrigger = link;
        const isSettingsModal = Boolean(link.closest('.alece-settings, .recovery-page'));
        formContent.querySelectorAll('form').forEach((item) => { if (!item.hasAttribute('action')) item.setAttribute('action', url.href); });
        if (!overlay) {
          overlay = document.createElement('dialog');
          overlay.className = 'unified-dialog';
          overlay.setAttribute('aria-labelledby', 'dialog-title');
          attachModalBehavior(overlay, 'overlay');
          overlay.addEventListener('close', () => activeTrigger?.focus());
          overlay.addEventListener('submit', async (submitEvent) => {
            if (overlay.dataset.settingsModal !== 'true') return;
            const postingForm = submitEvent.target.closest('form');
            if (!postingForm || !overlay.contains(postingForm)) return;
            submitEvent.preventDefault();
            const submitButton = submitEvent.submitter || postingForm.querySelector('[type=submit]');
            if (submitButton?.disabled) return;
            if (submitButton) submitButton.disabled = true;
            postingForm.setAttribute('aria-busy', 'true');
            try {
              // O campo hidden name=action mascara HTMLFormElement.action. Ler o atributo real.
              const response = await fetch(postingForm.getAttribute('action') || window.location.href, {
                method: 'POST', credentials: 'same-origin',
                headers: {'X-Requested-With': 'XMLHttpRequest'},
                body: new FormData(postingForm),
              });
              if (response.redirected) {
                const redirected = new URL(response.url);
                if (redirected.pathname.startsWith('/entrar/') || redirected.pathname.startsWith('/login/')) window.location.assign(redirected.href);
                else window.location.reload();
                return;
              }
              if (!response.ok) throw new Error('HTTP ' + response.status);
              const resultPage = new DOMParser().parseFromString(await response.text(), 'text/html');
              const replacement = resultPage.querySelector('[data-dialog-content]');
              if (!replacement) throw new Error('Formulário não retornado pelo servidor');
              const previousAction = postingForm.getAttribute('action') || window.location.href;
              replacement.querySelectorAll('form').forEach((item) => { if (!item.hasAttribute('action')) item.setAttribute('action', previousAction); });
              overlay.replaceChildren(replacement);
              syncGrantBlocks(overlay);
              bindAIProviderFields(overlay);
              snapshotForms(overlay);
              window.AleceModal.linkErrors(overlay);
              window.AleceModal.labelDialog(overlay);
              overlay.querySelector('[aria-invalid=true], .errorlist, [role=alert], input:not([type=hidden])')?.focus?.();
            } catch (error) {
              const status = /^HTTP (\d{3})$/.exec(error?.message || '')?.[1];
              const state = status === '403' ? 'forbidden' : status === '409' ? 'conflict' : 'error';
              const message = state === 'forbidden' ? 'Sem permissão para concluir esta operação. Nenhuma alteração foi confirmada.' :
                state === 'conflict' ? 'Conflito com dados atualizados. Recarregue a página antes de tentar novamente.' :
                  'Não foi possível concluir a operação. Revise os dados ou consulte os logs locais.';
              window.AleceModal.notify(message, state, overlay);
            } finally {
              postingForm.removeAttribute('aria-busy');
              if (submitButton) submitButton.disabled = false;
            }
          });
          document.body.append(overlay);
        }
        overlay.dataset.settingsModal = isSettingsModal ? 'true' : 'false';
        overlay.replaceChildren(formContent);
        syncGrantBlocks(overlay);
        bindAIProviderFields(overlay);
        snapshotForms(overlay);
        window.AleceModal.linkErrors(overlay);
        window.AleceModal.labelDialog(overlay);
        if (!overlay.open) overlay.showModal();
        syncModalScroll();
        const first = overlay.querySelector('[aria-invalid="true"], input:not([type="hidden"]), select, textarea');
        window.AleceModal.focusStart(overlay, first);
      } catch (_) {
        window.location.assign(url.href);
      } finally {
        opening = false;
      }
    });
  }

  // Changing the transfer profile reloads account choices in the same modal.
  // The server revalidates profile ownership and permissions on every request.
  document.addEventListener('change', async (event) => {
    const select = event.target.closest?.('select[data-profile-refresh]');
    if (!select) return;
    const form = select.closest('form');
    if (!form) return;
    const url = new URL(form.getAttribute('action') || window.location.href, window.location.href);
    if (select.value) url.searchParams.set('profile_id', select.value);
    else url.searchParams.delete('profile_id');
    const modal = select.closest('dialog[open]');
    if (!modal) {window.location.assign(url.href); return;}
    try {
      const response = await fetch(url, {credentials: 'same-origin', headers: {'X-Requested-With': 'XMLHttpRequest'}});
      if (!response.ok) throw new Error('Profile unavailable');
      const page = new DOMParser().parseFromString(await response.text(), 'text/html');
      const replacement = page.querySelector('[data-dialog-content]');
      if (!replacement) throw new Error('Form unavailable');
      replacement.querySelectorAll('form').forEach((item) => {
        if (!item.hasAttribute('action')) item.setAttribute('action', url.origin + url.pathname);
      });
      modal.replaceChildren(replacement);
      snapshotForms(modal);
      window.AleceModal.linkErrors(modal);
      window.AleceModal.labelDialog(modal);
      modal.querySelector('select[data-profile-refresh]')?.focus();
    } catch (_) {
      window.location.assign(url.href);
    }
  });

  // Permissões em perfis: os checkboxes são atalhos de edição em massa.
  // Níveis individuais são a única fonte de verdade para o backend.
  const syncGrantBlock = (block) => {
    const selects = [...block.querySelectorAll('select[data-grant-module]')];
    const view = block.querySelector('input[data-grant-bulk="view"]');
    const edit = block.querySelector('input[data-grant-bulk="edit"]');
    if (!selects.length || !view || !edit) return;
    const levels = selects.map((select) => select.value);
    const allView = levels.every((level) => level !== 'none');
    const allEdit = levels.every((level) => level === 'edit');
    view.checked = allView;
    view.indeterminate = !allView && levels.some((level) => level !== 'none');
    edit.checked = allEdit;
    edit.indeterminate = !allEdit && levels.some((level) => level === 'edit');
  };
  const syncGrantBlocks = (rootScope) => {
    rootScope.querySelectorAll('[data-grant-profile]').forEach(syncGrantBlock);
  };
  document.addEventListener('change', (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const block = target.closest('[data-grant-profile]');
    if (!block) return;
    const selects = [...block.querySelectorAll('select[data-grant-module]')];
    if (target.matches('input[data-grant-bulk="edit"]')) {
      // Marcar Editar concede edição em todos os módulos; desmarcar retira
      // a edição em todos eles, mas preserva a visualização.
      selects.forEach((select) => {
        if (target.checked) select.value = 'edit';
        else if (select.value === 'edit') select.value = 'view';
      });
    } else if (target.matches('input[data-grant-bulk="view"]')) {
      // Visualizar eleva módulos sem acesso; não reduz módulos que já editam.
      selects.forEach((select) => {
        if (!target.checked) select.value = 'none';
        else if (select.value === 'none') select.value = 'view';
      });
    } else if (!target.matches('select[data-grant-module]')) {
      return;
    }
    syncGrantBlock(block);
  });
  syncGrantBlocks(document);

  // Importação com drag and drop e clique; o Django continua responsável pela prévia.
  // requestSubmit executa validação nativa e preserva o CSRF do formulário multipart.
  const importForm = document.querySelector('[data-import-auto-form]');
  if (importForm) {
    const input = importForm.querySelector('[data-import-file]');
    const dropZone = importForm.querySelector('[data-import-drop-zone]');
    const feedback = importForm.querySelector('[data-import-feedback]');
    const importChoice = importForm.querySelector('[data-import-profile-choice]');
    const importLabel = importForm.querySelector('[data-import-profile-label]');
    const maxSize = 5 * 1024 * 1024;
    const extensions = /\.(csv|ofx|pdf)$/i;
    let submitting = false;
    let dragDepth = 0;
    const showStatus = (message, mode) => {
      feedback.textContent = message;
      feedback.classList.toggle('is-error', mode === 'error');
      feedback.classList.toggle('is-working', mode === 'working');
    };
    const upload = (file) => {
      if (submitting || !file) return;
      if (importChoice && !importChoice.value) {
        input.value = '';
        showStatus('Selecione um perfil financeiro antes de importar.', 'error');
        importChoice.focus();
        return;
      }
      if (!extensions.test(file.name)) {
        input.value = '';
        showStatus('Formato não suportado. Selecione um arquivo CSV, OFX ou PDF.', 'error');
        return;
      }
      if (file.size === 0 || file.size > maxSize) {
        input.value = '';
        showStatus('O arquivo precisa ter conteúdo e no máximo 5 MiB.', 'error');
        return;
      }
      submitting = true;
      dropZone.classList.add('is-busy');
      dropZone.setAttribute('aria-busy', 'true');
      showStatus(`Enviando ${file.name} e preparando a prévia para revisão…`, 'working');
      try {
        if (typeof importForm.requestSubmit === 'function') importForm.requestSubmit();
        else importForm.submit();
      } catch (error) {
        submitting = false;
        dropZone.classList.remove('is-busy');
        dropZone.removeAttribute('aria-busy');
        showStatus('Não foi possível iniciar o envio. Tente novamente.', 'error');
      }
    };
    if (importChoice) importChoice.addEventListener('change', () => {
      const chosen = importChoice.selectedOptions[0];
      const url = chosen?.dataset.uploadUrl;
      importForm.action = url || window.location.href;
      if (importLabel) importLabel.textContent = url ? chosen.textContent.trim() : 'Selecione acima';
      input.value = '';
      showStatus(url ? 'Perfil selecionado. Escolha ou arraste o arquivo para iniciar a prévia.' :
        'Selecione um perfil financeiro antes de importar.');
    });
    input.addEventListener('change', () => upload(input.files[0]));
    // Impede que o navegador abra o arquivo ao soltá-lo fora da zona.
    for (const eventName of ['dragover', 'drop']) {
      window.addEventListener(eventName, (event) => {
        if (event.dataTransfer && [...(event.dataTransfer.items || [])].some(item => item.kind === 'file')) {
          event.preventDefault();
          if (eventName === 'dragover' && !dropZone.contains(event.target)) event.dataTransfer.dropEffect = 'none';
        }
      });
    }
    dropZone.addEventListener('dragenter', (event) => {
      event.preventDefault();
      if (submitting) return;
      dragDepth += 1;
      dropZone.classList.add('is-dragover');
    });
    dropZone.addEventListener('dragover', (event) => {
      event.preventDefault();
      if (event.dataTransfer) event.dataTransfer.dropEffect = submitting ? 'none' : 'copy';
    });
    dropZone.addEventListener('dragleave', () => {
      dragDepth = Math.max(0, dragDepth - 1);
      if (!dragDepth) dropZone.classList.remove('is-dragover');
    });
    dropZone.addEventListener('drop', (event) => {
      event.preventDefault();
      dragDepth = 0;
      dropZone.classList.remove('is-dragover');
      if (submitting) return;
      const files = event.dataTransfer?.files;
      if (!files || files.length !== 1) {
        showStatus('Solte somente um arquivo por vez.', 'error');
        return;
      }
      try {
        const transfer = new DataTransfer();
        transfer.items.add(files[0]);
        input.files = transfer.files;
        upload(input.files[0]);
      } catch (error) {
        showStatus('Este navegador não conseguiu receber o arquivo. Clique na área para selecioná-lo.', 'error');
      }
    });
    window.addEventListener('pageshow', (event) => {
      if (!event.persisted) return;
      submitting = false;
      dragDepth = 0;
      input.value = '';
      dropZone.classList.remove('is-busy', 'is-dragover');
      dropZone.removeAttribute('aria-busy');
      showStatus('A análise da prévia começa automaticamente após selecionar um arquivo.');
    });
  }

  // Recovery codes remain in HTML only for the issuance response. Never send code text to server.
  document.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-recovery-copy], [data-recovery-download]');
    if (!button) return;
    const container = button.closest('[data-dialog-content]');
    if (!container) return;
    const codes = [...container.querySelectorAll('[data-recovery-code]')].map(el => el.textContent.trim());
    if (codes.length !== 6) return;
    const text = ['ALECE - Códigos de recuperação', 'Cada código pode ser usado apenas uma vez.', '', ...codes].join('\n') + '\n';
    const form = container.querySelector('[data-recovery-confirm-form]');
    if (!form) return;
    if (button.matches('[data-recovery-copy]')) {
      try {
        if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(text);
        else {
          const temp = document.createElement('textarea');
          temp.value = text; document.body.append(temp); temp.select();
          const ok = document.execCommand('copy'); temp.remove();
          if (!ok) throw new Error('clipboard unavailable');
        }
        form.elements.namedItem('copied').value = '1';
      } catch (_) { window.AleceModal.notify('Não foi possível copiar. Verifique a permissão da área de transferência.', 'error', container); }
    } else {
      const blob = new Blob([text], {type:'text/plain;charset=utf-8'});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url;
      a.download = 'ALECE_codigos_recuperacao.txt'; document.body.append(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 30000);
      form.elements.namedItem('downloaded').value = '1';
    }
    const copied = form.elements.namedItem('copied').value === '1';
    const downloaded = form.elements.namedItem('downloaded').value === '1';
    const confirm = form.querySelector('[data-recovery-confirm]');
    if (confirm) confirm.disabled = !(copied && downloaded);
    const state = container.querySelector('[data-recovery-state]');
    if (state) state.textContent = `Copiado: ${copied ? 'sim' : 'não'} · Download solicitado: ${downloaded ? 'sim' : 'não'}`;
  });
  const bindAIProviderFields = (scope) => {
    scope.querySelectorAll('[data-ai-form]').forEach((form) => {
      if (form.dataset.aiFormBound === '1') return;
      form.dataset.aiFormBound = '1';
      const select = form.querySelector('[data-ai-provider-select]');
      const script = form.querySelector('#ai-provider-presets');
      if (!select || !script) return;
      let presets = {};
      try { presets = JSON.parse(script.textContent); } catch (_) { return; }
      const customGroups = [...form.querySelectorAll('[data-ai-custom-group]')];
      const preview = form.querySelector('[data-ai-preset-summary]');
      let previous = select.value;
      const sync = () => {
        const preset = presets[select.value];
        // Ao sair de um preset, não copiar implicitamente endpoint/modelo/chave de outro provedor.
        if (!preset && previous !== 'custom') {
          customGroups.forEach((group) => group.querySelectorAll('input').forEach((input) => { input.value = ''; }));
        }
        previous = select.value;
        customGroups.forEach((group) => { group.hidden = Boolean(preset); });
        customGroups.forEach((group) => group.querySelectorAll('input').forEach((input) => { input.disabled = Boolean(preset); }));
        if (preview) preview.hidden = !preset;
        if (preset) {
          const name = preview.querySelector('[data-ai-preset-name]');
          const endpoint = preview.querySelector('[data-ai-preset-endpoint]');
          const model = preview.querySelector('[data-ai-preset-model]');
          if (name) name.textContent = preset.name;
          if (endpoint) endpoint.textContent = preset.endpoint;
          if (model) model.textContent = preset.model;
        }
      };
      select.addEventListener('change', sync);
      sync();
    });
  };
  bindAIProviderFields(document);
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
      // Não registrar pagamento ao marcar conta; só botão explícito confirma o POST.
    };
    amount.addEventListener('input', () => update(false));
    choices.forEach((choice) => choice.addEventListener('change', () => update(true)));
    update(false);
  }

  // Global "Ocultar valores" toggle (AT-155)
  const privacyToggles = document.querySelectorAll('[data-privacy-toggle-global]');
  let isPrivate = document.body.classList.contains('is-private');
  try { isPrivate = localStorage.getItem('alece-privacy') === 'true'; } catch (_) { /* Optional preference. */ }
  const applyPrivacy = () => {
    document.body.classList.toggle('is-private', isPrivate);
    privacyToggles.forEach((privacyToggle) => {
      privacyToggle.setAttribute('aria-pressed', String(isPrivate));
      privacyToggle.setAttribute('aria-label', isPrivate ? 'Mostrar valores' : 'Ocultar valores');
      privacyToggle.title = isPrivate ? 'Mostrar valores' : 'Ocultar valores';
      const icon = privacyToggle.querySelector('use');
      if (icon) icon.setAttribute('href', isPrivate ? '#i-eyeoff' : '#i-eye');
      else privacyToggle.textContent = isPrivate ? 'Mostrar valores' : 'Ocultar valores';
    });
  };
  applyPrivacy();
  privacyToggles.forEach((privacyToggle) => privacyToggle.addEventListener('click', () => {
    isPrivate = !isPrivate;
    applyPrivacy();
    try { localStorage.setItem('alece-privacy', String(isPrivate)); } catch (_) {}
  }));

  // Also apply to payment form toggle for consistency
  const paymentPrivacyToggle = document.querySelector('[data-privacy-toggle]');
  if (paymentPrivacyToggle) {
    paymentPrivacyToggle.addEventListener('click', (event) => {
      const hidden = document.body.classList.toggle('is-private');
      event.currentTarget.setAttribute('aria-pressed', String(hidden));
      event.currentTarget.textContent = hidden ? 'Mostrar valores' : 'Ocultar valores';
    });
  }
})();
