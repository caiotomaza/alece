# ALECE — Modal de renda dos perfis financeiros

## Objetivo e escopo

Substitui **apenas o fluxo do botão de edição de Renda da Visão geral**. A navegação não leva mais ao seletor de perfis: abre `dialog#overview-income-dialog` sobre o dashboard, com o título "Renda dos perfis financeiros", uma linha por perfil autorizado, e os comandos Cancelar e Salvar. A opção anterior de edição individual pela rota `finance:income-edit` permanece compatível em outras telas. Demais seletores de perfil permanecem como estavam.

A interface utiliza `alece_tokens.css`, `alece_components.css`, `alece_modals.css` e regras específicas em `alece_overview.css` para ambos os temas. Campo vazio significa renda desconhecida, diferentemente de zero. Não há alteração em fórmulas financeiras, contas ou movimentações.

## Backend

- Rota GET/POST: `finance:income-bulk` (`/financas/nucleos/<workspace_id>/rendas/`). O URL real inclui o prefixo do roteador em uso.
- Fonte de autorização: `get_module_profiles(user, "overview", "edit")`, filtrando `workspace_id`, exclusão lógica e arquivamento.
- O servidor reaplica permissões, exige correspondência exata da lista de IDs e presença dos campos de todos os perfis autorizados, valida cada campo com `IncomeForm`, bloqueia os registros e grava mudanças por `update_income` dentro de `transaction.atomic()`; o serviço preexistente registra auditoria sem revelar valores em seus detalhes.
- Respostas AJAX são JSON com `ok` e erros de campo para 422/409. Sem JavaScript, o link abre `income_bulk_edit.html` com POST e CSRF normais.
- As rendas de todos os perfis autorizados do núcleo são exibidas mesmo quando a Visão geral está filtrada para um único perfil. A seleção de navegação não é alterada.
- Nenhum dado de renda é enviado a serviços terceiros. Não há PWA, telemetria ou novos frameworks.

## Comportamento

O modal usa `showModal()` para bloquear interação com o fundo, controla a rolagem e restaura o foco no atalho Renda. Escape e clique fora acionam a proteção de alterações pendentes usando a confirmação existente (Salvar/Descartar/Continuar editando). Não salva ao fechar automaticamente. Um único Salvar envia os valores de todos os campos da operação, em uma única transação. Falhas HTTP e erros de campo não fecham o modal; sem JS, os erros são exibidos no formulário normal.

## Arquivos de implementação

- `src/controller/apps/finance/views.py`, `src/controller/apps/finance/urls.py` — endpoint, permissões, validação e contexto.
- `src/view/templates/finance/workspace_page.html` — atalho e `dialog` na Visão geral.
- `src/view/templates/finance/_income_bulk_form.html` — formulário reutilizável.
- `src/view/templates/finance/income_bulk_edit.html` — fallback progressivo.
- `src/view/static/finance/alece_overview.css` — aparência responsiva.
- `src/view/static/finance/alece_overview_income.js` — comportamento sem dependências novas.
- `tests/finance/test_income_bulk_modal.py` — testes Django (pendentes de infraestrutura).
- `tests/ui/test_income_bulk_contract.py` — testes estáticos executáveis sem banco.
- `tests/finance/test_all_profiles_actions.py` — contrato existente atualizado para nova rota.
- `scripts/quality/test_income_popup_preview.py`, `tests/browser/fixtures/income_modal_preview.html` — teste de Chromium em dados sintéticos.

## Referências

- Django 5.2: validação de forms, CSRF e transações atômicas (`docs.djangoproject.com/en/5.2/`).
- WHATWG/MDN: `HTMLDialogElement.showModal`, foco e backdrop (`developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog`).
