# Panorama Técnico Consolidado do ALECE — Para Auditoria Independente e Planejamento do Sprint 04

**Documento:** Panorama de Arquitetura, Engenharia, Domínio Financeiro e Evidências do ALECE  
**Destinatário:** Auditoria Técnica Independente / ChatGPT (para emissão de parecer e elaboração do prompt do Sprint 04)  
**Versão Atual:** `0.5.0 (Sprint 03 Concluído)`  
**Data:** 18 de outubro de 2026  
**Branch:** `codex/sprint01-audit-sprint02`  
**Licença:** GNU General Public License v3 (`GPL-3.0-only`) — Cópia integral em `LICENSE`  

---

## 1. Identificação Geral do Projeto e Filosofia de Engenharia

O **ALECE** é uma plataforma de gestão financeira pessoal e familiar, gratuita, de código aberto e projetada para auto-hospedagem (*self-hosted*), com suporte nativo a servidores Linux e implantação orientada a containers no ecossistema ZimaOS.

### Princípios Inegociáveis de Arquitetura:
1. **Monólito Modular Django 5.2 LTS + PostgreSQL 16**:
   - As *views* apenas autenticam, validam permissões por objeto e renderizam templates com melhoria progressiva.
   - Os *serviços transacionais* (`apps/finance/services/`) são a única fronteira autorizada para mutações no banco de dados, aplicando controle de concorrência com bloqueio pessimista (`select_for_update()`).
   - O *domínio puro* (`apps/finance/domain/`) realiza todos os cálculos matemáticos utilizando estritamente a classe `Decimal`, com quantização para duas casas decimais e arredondamento `ROUND_HALF_UP`.
   - **Nenhum saldo ou movimentação é alterado diretamente em views ou Django signals**.
2. **Imutabilidade e Trilha de Auditoria**:
   - Todo movimento de dinheiro gera lançamentos em partidas dobradas (`JournalEntry`).
   - O banco de dados PostgreSQL impõe balanceamento estrito (`SUM(debit) == SUM(credit)`) via trigger PL/pgSQL diferido (`finance_assert_journal_balance`).
   - Registros contábeis postados são **imutáveis**: um trigger `BEFORE UPDATE OR DELETE` (`finance_guard_posted_history`) rejeita qualquer tentativa de alteração ou exclusão direta no banco. Correções exigem **estorno oficial** (`reverse_batch`).
3. **Semântica Financeira de Dinheiro Desconhecido**:
   - Saldo ou renda não informada (`NULL`) é ontologicamente diferente de valor igual a zero (`Decimal('0.00')`).
   - O sistema nunca presume saldo zero para contas não informadas e nunca soma patrimônio ou saldo bancário à renda mensal.
4. **Isolamento e Segurança Multi-Perfil**:
   - Um usuário administrador acessa todos os perfis do seu próprio *workspace*.
   - Usuários comuns necessitam de concessão explícita de permissão (`ProfileGrant`) por perfil e por módulo.
   - Nenhuma requisição confia em IDs fornecidos pelo cliente: toda consulta e mutação valida o isolamento de tenant em nível de objeto.
5. **Fidelidade ao Protótipo Visual (v1.32.1)**:
   - A interface ativa preserva o design system documentado em `reference/prototype/ALECE_Prototipo_Visual_v1.32.1.html`: tokens de cores Claro/Escuro, navegação lateral (sidebar), botão `+` por seção, lápis de ação (`✎`) por linha e diálogos modais com ações agrupadas no rodapé.

---

## 2. Histórico Evolutivo do Projeto até o Sprint 03

- **Sprint 01 (Auditoria e Segurança Fundamental)**:
  - Eliminação de vulnerabilidades críticas de emissão anônima de códigos de recuperação e proteção contra ataques de força bruta com limitação persistente por IP/usuário.
  - Implementação de permissões por workspace e proteção contra escrita financeira arbitrária no Django Admin.
  - Aprovação do Gate A com 69 testes unitários e de integração no PostgreSQL.
- **Sprint 02 (Cadastros, Catálogos e Planejamento Orçamentário)**:
  - Modelagem e CRUD seguro de contas bancárias, despesas previsíveis (dia 1–31 com tratamento de meses curtos), despesas imprevisíveis com data do servidor e posições de investimento.
  - Implementação da política da Reserva de Emergência (6 a 12 meses de despesas essenciais, padrão 9 meses) e divisão dos excedentes orçamentários entre metas financeiras.
  - Interface com melhoria progressiva, temas Claro e Escuro, e migração `finance.0002_sprint02_catalogs`. Suíte ampliada para 90 testes.
- **Sprint 03 (Transações, Ledger Contábil, Permissões Granulares e E2E — CONCLUÍDO)**:
  - Implementação completa da engine contábil: pagamentos parciais e divididos entre múltiplas contas, controle de competências mensais, quitação, estornos simétricos, transferências e resgates.
  - Granularidade de permissões por módulo (`overview`, `accounts`, `expenses`, `investments`, `movements`) com níveis `none`, `view` e `edit`.
  - Conclusão dos dois ajustes críticos identificados no teste autenticado em navegador: distinção de saldo desconhecido de saldo zero e integração do estorno de movimentações ao modal de edição de movimentação.
  - Suíte validada com **109 testes aprovados no PostgreSQL 16**, CI local, hash-pinning de dependências e 48 evidências visuais capturadas em navegador headless Edge.

---

## 3. Arquitetura de Software e Estrutura de Diretórios

```text
c:\Users\Caio Tomaz\Desktop\projetos\pessoal\alece
├── apps/
│   ├── core/                          # Autenticação, perfis de usuário, auditoria de tentativas, permissões
│   │   ├── auth_forms.py              # Formulários de login, troca de senha e recuperação offline
│   │   ├── auth_services.py           # Regras de limitação de taxa e quotas de autenticação
│   │   ├── auth_views.py              # Views de sessão e códigos de recuperação
│   │   ├── permissions.py             # Matriz de autorização por workspace, perfil e módulo
│   │   └── models.py                  # UserProfile e AuthenticationAttempt
│   └── finance/                       # Core da aplicação financeira
│       ├── domain/                    # Domínio puro (sem dependência de ORM/framework)
│       │   ├── calculations.py        # Cálculos de reserva, alocação mensal e quantização Decimal
│       │   └── planning.py            # Tratamento de calendário, vencimentos e estimativa de metas
│       ├── services/                  # Casos de uso transacionais (fronteira exclusiva de escrita)
│       │   ├── accounts.py            # Criação de contas com lock pessimista
│       │   ├── grants.py              # Gestão transacional de permissões granulares
│       │   ├── ledger.py              # Saídas, transferências, resgates, estornos e partidas dobradas
│       │   ├── metrics.py             # Modelo de leitura com distinção estrita de NULL vs 0.00
│       │   ├── monthly.py             # Compromissos e quitações por competência mensal
│       │   ├── profiles.py            # Ciclo de vida e limite de perfis ativos por núcleo
│       │   └── records.py             # CRUD protegido de entidades cadastrais
│       ├── models.py                  # Entidades persistidas, checks, constraints e triggers
│       ├── forms.py                   # Formulários de cadastros e filtros
│       ├── transaction_forms.py       # Formulários de pagamentos multi-conta, transferências e resgates
│       ├── views.py                   # Views principais (visão geral, despesas, investimentos, movimentações)
│       ├── grant_views.py             # Telas de gestão de permissões para membros comuns
│       ├── transaction_views.py       # Views de pagamento, transferência, resgate, estorno e modal
│       ├── urls.py                    # Roteamento seguro da aplicação
│       └── migrations/                # 0001 a 0004 com integridade referencial e triggers PL/pgSQL
├── config/                            # Configurações Django (settings.py, test_settings.py, urls.py, wsgi.py)
├── docs/                              # Documentação de arquitetura, domínio, segurança, ADRs e relatórios
│   ├── reviews/                       # SPRINT01_AUDIT, SPRINT02_REPORT, SPRINT03_REPORT, PROGRESS, PANORAMA
│   │   └── screenshots/               # 48 capturas de tela E2E em 320, 390, 768 e 1440 pixels
│   └── SPEC_ORIGINAL_COMPLETA.md      # Especificação de requisitos original do projeto
├── reference/prototype/               # Protótipo interativo HTML/CSS/JS v1.32.1 original
├── requirements/                      # development.in/.lock e production.in/.lock com hashes SHA-256
├── scripts/                           # Scripts operacionais (bootstrap, deploy, backup, capturas E2E)
├── static/finance/                    # Estilos CSS de tema claro/escuro e script alece.js progressivo
├── templates/finance/                 # Templates Django auditados e acessíveis
└── tests/                             # 109 testes automatizados (unitários, integração, concorrência, E2E)
```

---

## 4. Modelagem de Dados, Constraints e Triggers PostgreSQL

### Principais Entidades:
1. **`Workspace` & `WorkspaceMembership`**:
   - Isolamento de núcleo familiar. Papéis: `admin` (acesso irrestrito aos perfis do núcleo) e `common` (depende de grants).
2. **`FinancialProfile`**:
   - Perfil financeiro individual (até 5 ativos por workspace, com lock pessimista no workspace na criação/reativação).
   - Possui `monthly_income` (`NULL` para desconhecido, `0.00` para sem renda, ou valor positivo).
3. **`BankAccount`**:
   - Contas bancárias e dinheiro físico. Campos: `balance` (saldo atual), `opening_balance` (saldo inicial de abertura). Possui constraint `ck_bank_balance_non_negative`.
4. **`RecurringExpense` & `MonthlyExpense`**:
   - `RecurringExpense`: Despesa mensal cadastrada (dia de vencimento 1 a 31).
   - `MonthlyExpense`: Snapshot da despesa na competência mensal (`YYYY-MM-01`), permitindo pagamentos e histórico precisos mesmo que o cadastro original seja alterado posteriormente.
5. **`UnexpectedExpense`**:
   - Despesa pontual com data registrada pelo servidor. O cadastro representa obrigação pendente e não debita saldo.
6. **`InvestmentPosition` & `MonthlyInvestmentPlan`**:
   - Categorias: `reserve` (Reserva de Emergência), `short_term`, `medium_term`, `long_term`.
   - Campos: `applied_amount` (custo de aquisição), `current_value` (saldo líquido atual), `target_amount` (meta, obrigatória nula para Reserva, cuja meta é calculada pelo sistema).
7. **`TransactionBatch`**:
   - Lote atômico de movimentação financeira.
   - Tipos: `recurring`, `unexpected`, `application`, `withdrawal`, `transfer`, `income`, `reversal`.
   - Campos: `amount`, `occurred_on`, `competence_month`, `idempotency_key` (única), `reversal_of` (vínculo simétrico 1:1 para estornos).
8. **`LedgerLeg`**:
   - Perna bancária individual do lote. Armazena a conta e o `delta` (negativo para débito, positivo para crédito).
9. **`JournalEntry`**:
   - Registro de partida dobrada (`account_code`, `debit`, `credit`, `bank_account`).
10. **`ProfileGrant`**:
    - Concessão de direitos por módulo para membros comuns: `overview_level`, `accounts_level`, `expenses_level`, `investments_level`, `movements_level` (`none`, `view`, `edit`).

### Triggers em PL/pgSQL no PostgreSQL:
- **`finance_assert_journal_balance`**: Disparado deferred após manipulações em `JournalEntry`. Impede commits onde `SUM(debit) != SUM(credit)`.
- **`finance_guard_posted_history`**: Disparado antes de `UPDATE` ou `DELETE` em `TransactionBatch`, `LedgerLeg` e `JournalEntry`. Rejeita qualquer mutação direta levantando exceção: `"Posted financial history is immutable"`.

---

## 5. Implementação Completa dos Fluxos Financeiros no Sprint 03

### 5.1. Pagamentos Parciais e Divididos entre Múltiplas Contas (`confirm_outflow`)
- O usuário escolhe o item da competência a ser pago.
- O formulário inteligente calcula a quantia restante devida (`due - paid`) e lista as contas bancárias com saldos disponíveis.
- A requisição submete um dicionário de splits `{account_id: valor}`.
- O serviço bloqueia o perfil, valida que a soma dos splits cobre o montante solicitado, assegura que cada conta possui saldo individual suficiente, cria o lote `TransactionBatch`, gera as `LedgerLeg` debitando as contas, escreve as partidas dobradas em `JournalEntry` e atualiza os saldos das contas por subtração atômica.
- Se o montante acumulado pago atinge o valor devido, o compromisso é marcado como quitado (exibindo checkbox preenchido `☑` no painel).

### 5.2. Transferências entre Contas (`transfer`)
- O usuário seleciona conta de origem, conta de destino e valor.
- O serviço valida que as contas são distintas e pertencem ao mesmo perfil financeiro autenticado.
- Bloqueia ambas as contas e o perfil com `select_for_update()`.
- Gera lote do tipo `transfer`, deduzindo da conta de origem e creditando na conta de destino, com lançamentos contábeis correspondentes, sem classificar receitas ou despesas artificiais.

### 5.3. Aplicações e Resgates de Investimento (`withdraw_investment`)
- **Aplicação**: Realiza a saída bancária (com suporte a split multi-conta) e credita simultaneamente o `applied_amount` e o `current_value` da posição financeira selecionada.
- **Resgate**: Valida que a posição possui saldo suficiente (`current_value >= valor`). Calcula a proporção do custo de aquisição baixado (`applied_amount * valor / current_value`), credita a conta bancária de destino e debita a posição de investimento.

### 5.4. Estornos Simétricos e Preservação do Histórico (`reverse_batch`)
- A anulação de movimentações não apaga nem edita linhas existentes.
- O serviço `reverse_batch` valida que a movimentação original não foi estornada anteriormente e não é ela própria um estorno.
- Cria um novo lote com `kind="reversal"` vinculado via `reversal_of`.
- Inverte os deltas de cada conta participante (devolvendo os valores debitados ou retirando os creditados).
- Se a movimentação envolvia posições de investimento, reverte o `applied_amount` e o `current_value` com proteção estrita contra saldos negativos.
- Registra partidas dobradas espelhadas (`credit` vira `debit` e vice-versa).
- A interface passa a marcar a movimentação original como `Estornado` e o novo lançamento como `Estorno`.

### 5.5. Idempotência e Prevenção de Concorrência
- Cada formulário transacional gera um token UUID único (`idempotency_key`).
- Se uma requisição com a mesma chave for reenviada (duplo clique, falha de rede), o serviço intercepta a chave única e retorna o lote já criado com segurança, impedindo lançamentos duplicados.
- Testes concorrentes com `ThreadPoolExecutor` e barreiras de thread provaram que requisições paralelas competindo pelo mesmo saldo são enfileiradas ou rejeitadas com segurança, sem gerar saldo negativo.

---

## 6. Resolução dos Dois Apontamentos do Teste em Navegador

### Ajuste 1: Distinção Rigorosa de Saldo Desconhecido vs Saldo Conhecido Zero
- **Arquivo Modificado:** `apps/finance/services/metrics.py`, `apps/finance/views.py`, `templates/finance/workspace_page.html`.
- **Comportamento Validado:**
  - Perfil sem contas ou com todas as contas com `balance=None`:
    - `summary["bank_balance"]` retorna `None`.
    - Visão Geral exibe: `Saldos conhecidos: Desconhecido` e `Saldo atual conhecido: Desconhecido`.
    - Projeção de saldo exibe: `—`.
  - Perfil com conta com saldo `Decimal('0.00')`:
    - `summary["bank_balance"]` retorna `Decimal('0.00')`.
    - Visão Geral exibe: `Saldos conhecidos: R$ 0,00` e `Saldo atual conhecido: R$ 0,00`.
    - Projeção de saldo exibe: `R$ -X,XX` ou `R$ 0,00` calculados a partir da base zero conhecida.

### Ajuste 2: Integração do Estorno de Movimentações ao Modal do Protótipo v1.32.1
- **Arquivos Criados/Modificados:** `apps/finance/transaction_views.py`, `apps/finance/urls.py`, `templates/finance/movement_detail.html`, `templates/finance/workspace_page.html`.
- **Comportamento Validado:**
  - O botão de envio inline de formulário foi removido da listagem de histórico.
  - Cada linha de movimentação recebeu o botão padrão de lápis (`✎`) com rótulo descritivo acessível.
  - O clique abre o modal `Editar movimentação` contendo: Tipo, Descrição, Data, Valor (R$), Situação, Contas envolvidas e o aviso de vínculo histórico.
  - O rodapé do modal agrupa os botões de ação:
    - Botão de perigo **Estornar** (acionado com diálogo nativo de confirmação `data-confirm-reversal`);
    - Botão secundário **Cancelar** (que fecha o modal).
  - A operação de estorno é executada via POST para `reverse-movement`, mantendo o histórico 100% imutável.

---

## 7. Relatório de Execução de Testes e Evidências

### 7.1. Suíte Automatizada (Pytest no PostgreSQL Efêmero)
- **Total de Testes:** **109 testes aprovados** (0 falhas, 0 erros, 8 subtestes).
- **Tempo de Execução:** ~26.38 segundos.
- **Cobertura:**
  - `test_auth.py` & `test_auth_security.py`: Segurança de autenticação, força bruta, troca de senha e recuperação offline.
  - `test_audit_permissions.py` & `test_sprint03_permissions.py`: Isolamento por workspace e matriz granular de grants por módulo.
  - `test_finance_services.py` & `test_calculations.py`: Cálculos financeiros de reserva e planejamento.
  - `test_ledger.py` & `test_sprint03_ledger.py`: Débitos, créditos, transferências, resgates, estornos, concorrência e constraints de banco.
  - `test_sprint03_views.py`: Jornadas autenticadas completas de navegador, distinção de saldo nulo vs zero, modal de edição e reversão.
  - `test_sprint03_preflight.py`: Preflight de migração estrita da Reserva legada.

### 7.2. Auditoria e Qualidade de Código
- `ruff check .`: **Aprovado (0 avisos, 0 erros)**.
- `python -m compileall -q apps config tests manage.py`: **Aprovado (0 erros)**.
- `python manage.py check`: **Aprovado (0 problemas identificados)**.
- `python manage.py makemigrations --check --dry-run`: **Aprovado (Nenhuma migração pendente ou drift)**.
- `python manage.py preflight_finance --strict`: **Aprovado (`safe_to_apply_reserve_constraint: true`, 0 pendências)**.
- `pip-audit -r requirements/production.lock`: **Aprovado (Nenhuma vulnerabilidade conhecida)**.
- `pip-audit -r requirements/development.lock`: **Aprovado (Nenhuma vulnerabilidade conhecida)**.
- `docker build --tag alece:sprint03-validate .`: **Aprovado (Build reproduzível com hash-pinning e collectstatic)**.

### 7.3. Evidências Visuais E2E (Navegador Headless Edge)
Foram capturadas **48 imagens de tela completas** salvas em `docs/reviews/screenshots/`:
- **Telas Inspecionadas:**
  1. Visão Geral (`overview`)
  2. Despesas (`expenses`)
  3. Investimentos (`investments`)
  4. Movimentações (`movements`)
  5. Perfil e Contas (`profile_detail`)
  6. Modal de Edição de Movimentação (`movement_detail_modal`)
- **Resoluções Testadas:**
  - 320x640 px (Mobile compacto)
  - 390x844 px (Mobile moderno)
  - 768x1024 px (Tablet)
  - 1440x900 px (Desktop)
- **Temas Validados:**
  - Tema Claro (`light`)
  - Tema Escuro (`dark`)
- **Inspeção Visual:**
  - Alinhamento rigoroso dos tokens de contraste, espaçamento e tipografia.
  - Inexistência de quebras de layout ou vazamentos horizontais (*horizontal overflow*) nas larguras de 320 e 390px.
  - Modais centrados, com backdrop opaco, cabeçalho de fechamento e rodapés alinhados.

---

## 8. Backups e Rastreabilidade de Estado

Em estrito cumprimento a `AGENTS.md`:
- **Log da Intervenção:** `C:/Users/Caio Tomaz/logs/2026-10-18_14-55-57__alece-sprint03-resume.log`
- **Backup de Código do Sprint 03:** `C:/Users/Caio Tomaz/backups/2026-10-18_14-55-57__alece-sprint03-resume.zip`
- **Hash SHA-256 Verificado:** `DE549D1378053EFFE1A33934C042981F2DC42F6ED27B416B16E01749E82DEC53`
- **Integridade de CRC:** Verificada e validada via PowerShell.
- Nenhum contêiner persistente de produção ou dados reais foi tocado durante toda a intervenção.

---

## 9. Escopo Recomendado para o Sprint 04

O Sprint 03 entregou a base financeira completa de transações manuais, conciliação de competências, permissões granulares e ledger contábil. O próximo salto natural para o projeto (Sprint 04) deve contemplar:

1. **Pipeline de Importação de Extratos Bancários**:
   - Suporte a upload seguro de arquivos nos formatos **OFX** e **CSV**.
   - Sanitização de arquivos, detecção de codificação (UTF-8, ISO-8859-1) e validação de schema.
   - Detecção de transações duplicadas baseada em FITID (OFX) ou hash de campos normalizados (Data + Valor + Descrição).
2. **Reconciliação Assistida e Associação de Lançamentos**:
   - Mecanismo para associar transações importadas a despesas previsíveis cadastradas, despesas imprevisíveis ou investimentos existentes.
   - Sugestão visual de conciliação para facilitar a quitação com 1 clique.
3. **Mecanismo de Categorização Automática (Regras de De-Para)**:
   - Criação de regras condicionais configuráveis por perfil (ex: se descrição contém "Supermercado X", categorizar como "Essencial").
4. **Relatórios Financeiros e DRE Simplificado**:
   - Gráficos e tabelas de evolução patrimonial e fechamento de competências anteriores.

---

## 10. Prompt Sugerido para Envio ao ChatGPT para Iniciar o Sprint 04

```text
Olá, ChatGPT. Por favor, atue como Arquiteto de Software e Auditor Financeiro Sênior do projeto ALECE.

Eu estou desenvolvendo o ALECE, uma plataforma de gestão financeira pessoal e familiar self-hosted, em monólito Django 5.2 LTS, PostgreSQL 16 e Docker Compose, sob licença GPL-3.0-only.

O Sprint 03 foi recentemente concluído e auditado com sucesso (109 testes passando no PostgreSQL, ledger com partidas dobradas imutáveis via triggers PL/pgSQL, pagamentos parciais e multi-conta, competências mensais, estornos simétricos, permissões granulares por módulo, 48 capturas de tela E2E responsivas de 320 a 1440px em temas Claro e Escuro, e preflight de migração aprovado). Todos os detalhes técnicos estão consolidados no arquivo docs/reviews/PANORAMA_ALECE_PARA_CHATGPT.md e docs/reviews/SPRINT03_REPORT.md.

Com base nesse contexto:
1. Faça uma análise crítica e auditoria independente do estado atual da arquitetura e das decisões de domínio financeiro documentadas.
2. Formule o plano de desenvolvimento detalhado e o prompt de execução para o SPRINT 04, que terá como foco:
   - Importação de extratos bancários (OFX e CSV) com proteção contra duplicidades (FITID / hash) e isolamento por conta/perfil;
   - Reconciliação bancária assistida com vínculo direto aos compromissos de competência mensal e despesas cadastradas;
   - Motor de regras de categorização inteligente (De-Para baseado em expressões/termos);
   - Preservação estrita das regras permanentes (monólito Django/PostgreSQL, Decimal puro, imutabilidade do ledger contábil, sem escrita em signals/views, sem dados reais e respeito ao protótipo visual v1.32.1).
```
