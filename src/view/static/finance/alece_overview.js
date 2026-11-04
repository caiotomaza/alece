/* SPDX-License-Identifier: GPL-3.0-only */
/* Melhoria progressiva: ao seguir o atalho de saldo, revela os detalhes nativos. */
(() => {
  'use strict';
  document.querySelectorAll('[data-overview-expand]').forEach((link) => {
    link.addEventListener('click', () => {
      const details = document.getElementById(link.dataset.overviewExpand);
      if (details instanceof HTMLDetailsElement) details.open = true;
    });
  });
})();
