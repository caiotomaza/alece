# Relatório de Conclusão e Auditoria — Sprint 03

**Projeto:** ALECE — Finanças Pessoais e Familiares  
**Data da Auditoria:** 18 de outubro de 2026  
**Ambiente de Execução:** Monólito Django 5.2 LTS, PostgreSQL 16 (Bookworm), Docker isolado sem portas expostas  
**Branch:** `codex/sprint01-audit-sprint02` (commit base: `afc96e830f5f809372accd11c56134063f3d512d`)  
**Licença:** GNU GPL v3 (`GPL-3.0-only`)  

---

## 1. Resumo Executivo e Objetivos do Sprint 03

O Sprint 03 teve como objetivo principal a entrega completa da camada de **Transações, Movimentações, Pagamentos, Competências Mensais e Permissões Granulares por Módulo**, transformando os cadastros e planejamentos estruturados no Sprint 02 em um sistema financeiro operacionalmente íntegro, estritamente auditável e imutável no banco de dados.

Todas as diretrizes permanentes de `AGENTS.md`, `docs/DOMAIN.md` e `docs/SPEC_ORIGINAL_COMPLETA.md` foram rigorosamente mantidas:
- Nenhum saldo ou movimentação é escrito em views ou signals: todas as mutações financeiras passam por serviços transacionais atômicos com bloqueio pessimista (`select_for_update()`).
- O domínio calcula tudo exclusivamente com `Decimal` e arredondamento explícito (`ROUND_HALF_UP`).
- Cadastros de despesa, renda ou posição não confirmam movimentação bancária por si sós.
- Dinheiro desconhecido (`NULL`) é mantido estritamente distinto de zero (`Decimal('0.00')`).
- Partidas dobradas balanceadas (`JournalEntry`) e imutabilidade auditável de lançamentos postados são garantidas por triggers em nível de banco de dados (`finance_assert_journal_balance` e `finance_guard_posted_history`).
- Estornos preservam 100% da trilha histórica por meio de lançamentos de reversão simétricos (`reverse_batch`).

---

## 2. Resolução dos Dois Apontamentos do Teste em Navegador

Durante os testes autenticados com navegador real, foram identificados dois refinamentos mandatórios que foram implementados, testados e validados:

### 2.1. Distinção Rigorosa entre Saldo Totalmente Desconhecido e Saldo Conhecido Igual a Zero
- **Diagnóstico:** Anteriormente, se um perfil financeiro possuía contas onde todos os saldos eram desconhecidos (`balance IS NULL`), a agregação de leitura aplicava um fallback `or ZERO`, exibindo erroneamente `R$ 0,00` nos cartões de métricas da Visão Geral.
- **Correção Implementada:**
  1. Em `apps/finance/services/metrics.py` (`profile_summary`), `has_known_balance` verifica se existe ao menos uma conta ativa com saldo preenchido (`balance__isnull=False`). Caso não haja, `bank_balance` é retornado estritamente como `None`.
  2. Em `apps/finance/views.py` (`workspace_page`), a consolidação do núcleo só soma seções que possuam saldo conhecido; se nenhuma tiver, o saldo total do núcleo é `None`.
  3. No template `templates/finance/workspace_page.html`, `{% if bank_balance is None %}` exibe textualmente `Desconhecido`, enquanto um saldo comprovadamente zero é formatado como `R$ 0,00`.
  4. O cálculo de `projected_balance` é mantido como `None` (exibindo `—`) caso o saldo base seja desconhecido, e exibe o aviso de `Projeção parcial: X saldo(s) desconhecido(s)` caso haja mistura de contas conhecidas e desconhecidas.

### 2.2. Integração do Estorno de Movimentações ao Modal de Edição (Protótipo v1.32.1)
- **Diagnóstico:** Na listagem de Movimentações (`/movements/`), havia sido inserido um botão direto de estorno por formulário inline na tabela, divergindo da especificação de componentes ativos do protótipo v1.32.1 (lápis de ação por linha e modal com ações no rodapé).
- **Correção Implementada:**
  1. A coluna de ação na tabela de `workspace_page.html` foi padronizada com o botão ícone de lápis (`✎`), direcionando para a rota de edição/detalhes da movimentação (`finance:movement-detail`).
  2. Criação da view `movement_detail` em `apps/finance/transaction_views.py` e template `templates/finance/movement_detail.html`, estruturado sob o padrão de melhoria progressiva (`<div class="dialog-fallback" data-dialog-content>` acoplado ao `<dialog class="unified-dialog" data-edit-dialog>`).
  3. O modal exibe todos os campos em conformidade com o protótipo: Tipo, Descrição/Nota, Data, Valor (R$), Situação (Confirmado, Estornado, Estorno) e Contas/Deltas vinculados, acompanhado do texto de ajuda: *"Movimentações vinculadas continuam associadas ao registro original. Para removê-las, use Estornar."*
  4. O rodapé do modal integra os botões de ação:
     - Botão de perigo **Estornar** (quando a movimentação for reversível, com confirmação nativa `data-confirm-reversal`);
     - Botão secundário **Cancelar** (que fecha o modal e retorna à listagem).
  5. Imutabilidade do Ledger: respeitando o trigger `finance_guard_posted_history`, movimentações postadas não aceitam mutação in-place; a view é somente leitura para revisão e o estorno é submetido via endpoint atômico `reverse_movement`.

---

## 3. Funcionalidades Financeiras Implementadas e Validadas

| Módulo / Funcionalidade | Implementação Técnica | Regra Financeira & Garantia |
|---|---|---|
| **Pagamentos Parciais e Quitação** | `confirm_outflow(kind='recurring')` | Permite abater parcelas sucessivas de uma despesa mensal até o limite do valor cadastrado ou do snapshot da competência. Quitação total marca o item como pago. |
| **Split Multi-Conta** | `splits={account_id: amount}` | Distribui o débito em múltiplas contas selecionadas pelo usuário. O serviço valida atômica e pessimistamente o saldo suficiente em cada conta. Não permite saldo negativo. |
| **Competências Mensais** | `MonthlyExpense` / `MonthlyInvestmentPlan` | Registra o valor devido do mês especificado (`YYYY-MM-01`). Permite que gastos fixos com alteração futura preservem os compromissos históricos passados. |
| **Despesas Imprevisíveis** | `confirm_outflow(kind='unexpected')` | Movimenta saída atrelada a uma despesa pontual. Impede pagamento superior ao valor registrado. Cadastrar não debita; confirmar quita. |
| **Aplicações de Investimento** | `confirm_outflow(kind='application')` | Debita contas bancárias e credita simultaneamente a posição (`applied_amount` e `current_value`), mantendo a partida dobrada balanceada. |
| **Resgates de Investimentos** | `withdraw_investment()` | Credita conta bancária de destino e debita a posição de investimento. Calcula a proporção do custo de aquisição baixado (`applied_amount * amount / current_value`). |
| **Transferências entre Contas** | `transfer()` | Movimenta saldo entre duas contas do mesmo perfil. Gera débito na origem e crédito no destino em partidas dobradas, sem classificar como receita ou despesa. |
| **Estornos Simétricos** | `reverse_batch()` | Reverte lançamentos contábeis criando um lote `reversal` apontando para `reversal_of`. Recompõe saldos e posições exatamente como no momento anterior. |
| **Idempotência Rigorosa** | `idempotency_key` (CharField unique) | Garante que requisições repetidas, reenvios de formulário ou timeouts de rede não dupliquem lançamentos nem débitos em conta. |
| **Permissões Granulares** | `ProfileGrant` (`none`/`view`/`edit`) | Autorização modular para `overview`, `accounts`, `expenses`, `investments` e `movements`. Administrador do workspace tem acesso total irrestrito. Usuário comum depende de concessão explícita. |

---

## 4. Auditoria de Banco de Dados, Schemas e Migrações

O banco de dados PostgreSQL 16 possui três migrações ativas na app `finance`:
1. `0001_initial.py`: Workspaces, Membros, Perfis Financeiros, Contas Bancárias e Grants básicos.
2. `0002_sprint02_catalogs.py`: Catálogos de despesas previsíveis, imprevisíveis, posições de investimento e política da Reserva.
3. `0003_bankaccount_opening_balance_and_more.py`: Adição de `opening_balance`, criação do ledger contábil (`TransactionBatch`, `LedgerLeg`, `JournalEntry`), triggers PL/pgSQL de balanceamento contábil e de imutabilidade estrita.
4. `0004_monthlyinvestmentplan_and_more.py`: Suporte a planos mensais de investimento por competência (`MonthlyInvestmentPlan`).

### Triggers PL/pgSQL Ativos
- `finance_assert_journal_balance()`: Executado como `CONSTRAINT TRIGGER DEFERRED` após inserções ou alterações em `finance_journalentry`. Garante matematicamente que `SUM(debit) == SUM(credit)` para cada lote antes do commit.
- `finance_guard_posted_history()`: Executado como trigger `BEFORE UPDATE OR DELETE` em `finance_transactionbatch`, `finance_ledgerleg` e `finance_journalentry`. Dispara `RAISE EXCEPTION 'Posted financial history is immutable'` caso qualquer instrução tente alterar registros postados que possuam autor registrado.

---

## 5. Resultados de Testes e Validações Executadas

Todas as verificações foram executadas no ambiente isolado e aprovadas sem exceção:

```text
========================================================================================
CHECKLIST DE VERIFICAÇÃO AUTOMATIZADA — SPRINT 03
========================================================================================
[OK] Compilação Python: python -m compileall -q apps config tests manage.py (0 erros)
[OK] Linting e Estilo: ruff check . (All checks passed!)
[OK] Django System Check: python manage.py check (0 issues)
[OK] Migration Drift: python manage.py makemigrations --check --dry-run (No changes detected)
[OK] Preflight Reserva Legada: python manage.py preflight_finance --strict (safe_to_apply: true, 0 rows)
[OK] Auditoria Dependências Produção: pip-audit -r requirements/production.lock (No known vulnerabilities)
[OK] Auditoria Dependências Desenvolvimento: pip-audit -r requirements/development.lock (No known vulnerabilities)
[OK] Suíte Pytest PostgreSQL: 109 passed, 55 warnings, 8 subtests passed in 26.38s
[OK] Docker Build Produção: docker build --tag alece:sprint03-validate . (hash-pinned, collectstatic ok)
[OK] E2E Visual Headless Edge: 48 capturas de tela geradas em docs/reviews/screenshots/
     - Resoluções: 320x640, 390x844, 768x1024, 1440x900
     - Temas: Claro (light) e Escuro (dark)
     - Telas: Visão geral, Despesas, Investimentos, Movimentações, Perfil e Modal de Edição
========================================================================================
```

---

## 6. Arquivos Criados e Modificados no Sprint 03

### Arquivos Modificados
- `.github/workflows/ci.yml`: Inclusão de preflight finance e verificação de hashes de dependências.
- `Dockerfile`: Fixação de hashes e atualização segura do instalador `pip==26.2.1`.
- `apps/core/permissions.py`: Matriz modular de permissões granulares (`user_can_module`, `require_module`, `get_module_profiles`).
- `apps/finance/admin.py`: Proteção de modelos de ledger contra escrita arbitrária via Django admin.
- `apps/finance/forms.py`: Validação de saldos e formulários de cadastros.
- `apps/finance/models.py`: Modelos `TransactionBatch`, `LedgerLeg`, `JournalEntry`, `MonthlyExpense`, `MonthlyInvestmentPlan`.
- `apps/finance/services/accounts.py`: Criação de contas com bloqueio pessimista e validação de nomes duplicados.
- `apps/finance/services/ledger.py`: Mecanismo transacional de débitos, créditos, transferências, resgates, estornos e journal balance.
- `apps/finance/services/metrics.py`: Resumo financeiro com distinção explícita entre `NULL` e `0.00`.
- `apps/finance/services/records.py`: Regras de negócio de cadastros com proteção contra exclusão de registros com histórico contábil.
- `apps/finance/urls.py`: Rotas de pagamento, estorno, transferência, resgate e modal de movimentações.
- `apps/finance/views.py`: Views principais com suporte à visualização por perfil, mês, consolidação e permissões.
- `requirements/development.in`, `development.txt`, `production.in`, `production.txt`: Dependências restritas.
- `static/finance/alece.css`: Adaptações responsivas de modal, tokens de tema claro/escuro e tabelas.
- `static/finance/alece.js`: Melhoria progressiva de modais, alternância de tema e confirmação de estorno.
- `templates/finance/base.html`: Estrutura de base e cabeçalho.
- `templates/finance/profile_detail.html`: Exibição de contas e saldo desconhecido vs zero.
- `templates/finance/workspace_page.html`: Telas unificadas com seletor de mês/perfil, lápis de ação e métricas.
- `tests/test_finance_services.py`, `tests/test_finance_views.py`, `tests/test_ledger.py`: Testes de regressão.
- `README.md`, `RUNBOOK.md`, `CHANGELOG.md`, `docs/reviews/PROGRESS.md`: Documentação operacional e de progresso.

### Arquivos Criados
- `apps/finance/grant_views.py`: Gestão de permissões de membros comuns pelo administrador do workspace.
- `apps/finance/transaction_forms.py`: Formulários para pagamentos multi-conta, transferências e resgates.
- `apps/finance/transaction_views.py`: Views autenticadas para pagamentos, transferências, resgates, estornos e modal de movimentações.
- `apps/finance/services/grants.py`: Serviço transacional de concessão e revogação de permissões granulares.
- `apps/finance/services/monthly.py`: Leitura de compromissos mensais e cálculo de valores devidos por competência.
- `apps/finance/management/commands/preflight_finance.py`: Comando CLI de verificação de integridade antes de migrações.
- `apps/finance/migrations/0003_bankaccount_opening_balance_and_more.py`: Migração de ledger e triggers PL/pgSQL.
- `apps/finance/migrations/0004_monthlyinvestmentplan_and_more.py`: Migração de planos mensais de investimento.
- `requirements/development.lock`, `requirements/production.lock`: Lockfiles auditados e pinados por hash.
- `templates/finance/grant_list.html`, `grant_edit.html`: Gestão visual de permissões granulares.
- `templates/finance/payment_form.html`: Formulário de pagamento parcial e multi-conta com alocação dinâmica.
- `templates/finance/transaction_form.html`: Formulário modal para transferências e resgates.
- `templates/finance/movement_detail.html`: Modal de edição e estorno de movimentações do protótipo v1.32.1.
- `scripts/capture_e2e_screenshots.py`: Automação de capturas de tela E2E em navegador Edge headless.
- `tests/seed_sprint03_browser.py`: Fixture sintética para ambiente E2E isolado.
- `tests/test_sprint03_ledger.py`, `test_sprint03_permissions.py`, `test_sprint03_preflight.py`, `test_sprint03_views.py`: Testes completos do Sprint 03.
- `docs/reviews/screenshots/*.png`: 48 arquivos de evidência visual em todas as resoluções e temas.

---

## 7. Riscos, Pendências e Não-Conformidades

### Riscos Mitigados no Sprint 03
1. **Risco de Dupla Contabilização:** Mitigado pelo uso de `idempotency_key` obrigatória em todo lote de saída, transferência ou estorno.
2. **Risco de Saldo Negativo:** Mitigado pela validação prévia de saldo disponível em cada perna bancária dentro de transação com `select_for_update()`.
3. **Risco de Adulteração de Histórico:** Mitigado por trigger de banco que proíbe `UPDATE` e `DELETE` em lotes e pernas de transação postadas.
4. **Risco de Vazamento entre Perfis:** Mitigado pela validação de pertencimento de cada conta/despesa ao perfil autenticado em nível de serviço.

### Pendências Conhecidas para os Próximos Sprints (Não Bloqueantes)
1. **Importação OFX e CSV (Sprint 04):** O sistema ainda não possui pipeline de upload de extratos bancários.
2. **Categorização Inteligente e Regras de De-Para (Sprint 04):** Classificação automática de extratos importados.
3. **Reconciliação Assistida (Sprint 04):** Associação visual entre lançamentos do extrato e despesas/aplicações cadastradas.
4. **Relatórios Consolidados Anuais (Sprint 05):** Demonstração do resultado do exercício e evolução patrimonial histórica.

---

## 8. Próximos Passos Imediatos

1. Registro do commit local final do Sprint 03 com todas as evidências anexadas.
2. Não executar push, tag ou deploy em produção (permanece em homologação local/isolada).
3. Submeter o panorama técnico `docs/reviews/PANORAMA_ALECE_PARA_CHATGPT.md` para auditoria externa independente e geração das diretrizes de desenvolvimento do Sprint 04.
