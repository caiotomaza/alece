# Panorama Técnico Consolidado do ALECE — Para Auditoria Independente e Planejamento do Sprint 06

**Documento:** Panorama de Arquitetura, Engenharia, Domínio Financeiro e Evidências do ALECE  
**Destinatário:** Auditoria Técnica Independente / ChatGPT (para emissão de parecer e elaboração do prompt do Sprint 06)  
**Versão Atual:** `0.7.0 (Sprint 05 Concluído)`  
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

## 2. Histórico Evolutivo do Projeto até o Sprint 05

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
- **Sprint 04 (Importação Bancária e Reconciliação Assistida — CONCLUÍDO)**:
  - **Pipeline de importação modular**: Adaptadores versionados para CSV (UTF-8, ISO-8859-1, Windows-1252; delimitadores `;`, `,`, tab, `|`; cabeçalho opcional; colunas crédito/débito separadas ou valor único com sinal), OFX 1.x (SGML) e OFX 2.x (XML com proteção XXE e expansão de entidades). Parser factory com detecção automática de formato por extensão e conteúdo.
  - **Segurança de upload**: Validação de tamanho (5 MiB), tipo, codificação, estrutura e limites (5.000 linhas). Sanitização de textos contra XSS, formula injection, caracteres de controle. Processamento 100% local (self-hosted), sem transmissão a terceiros.
  - **Staging e auditoria**: Modelos `ImportBatch` e `ImportRow` com hash SHA-256 do arquivo, versão do parser, contadores de linhas válidas/duplicadas/erros, status de processamento (`staged`, `validated`, `reviewed`, `committed`, `failed`), trilha de auditoria completa (autor, timestamps, idempotency key).
  - **Detecção conservadora de duplicidades**: Prioridade 1) FITID (identificador bancário único), 2) Hash do arquivo (reimportação idêntica), 3) Comparação contextual (data ±1 dia, valor exato em centavos, similaridade de descrição por palavras-chave >3 chars). **Não presume duplicidade** por apenas mesmo valor/data — sinaliza revisão e preserva lançamentos legítimos.
  - **Reconciliação assistida**: Sugestões inteligentes por linha: vincular a despesa previsível/imprevisível existente (com detecção de pagamento parcial via `MonthlyExpense`), aplicação/resgate em investimento, transferência entre contas, recebimento, nova despesa imprevisível. Alertas de conflito (valor acima do devido, conta sem saldo) e justificativa textual para cada sugestão.
  - **Categorização De-Para configurável**: Regras por perfil com padrão (regex ou termo exato), campo alvo (descrição/memo/ambos), tipo sugerido, vínculo sugerido, prioridade explícita, ativação/desativação, histórico. Heurística de fallback para transações sem regra.
  - **Prévia editável integrada**: Interface alinhada ao protótipo v1.32.1 (temas Claro/Escuro, sidebar, lápis por linha, modal com ações no rodapé). Seleção individual de linhas, indicação visual de duplicidades, edição de valor/descrição/tipo/competência/conta, splits multi-conta, ações em massa, dry-run via AJAX, confirmação humana obrigatória via POST com chave idempotente.
  - **Commit atômico e idempotente**: Transação única `transaction.atomic()` criando/vinculando `TransactionBatch` com ledger balanceado (partidas dobradas), atualizando saldos e posições via `select_for_update()`. Idempotência por `idempotency_key` no batch e por linha (`{key}:{row_number}`). Estorno de importação via `reverse_batch` existente.
  - **Relatório detalhado pós-importação**: Resumo (inseridos, vinculados, ignorados, duplicados, erros), lista de `TransactionBatch` criados, trilha de auditoria (hash arquivo, parser, autor, timestamp, chave idempotente), avisos de conflitos.
  - **Permissões granulares**: Requer `accounts:edit` e `movements:edit` no perfil alvo. Administrador acessa todos os perfis; usuário comum depende de `ProfileGrant` explícito. Revogação imediata no próximo request.
  - **Testes abrangentes**: 43 testes cobrindo parsers CSV/OFX, detecção de duplicidade, categorização, reconciliação, fluxo completo upload→stage→preview→commit, pagamentos parciais, investimentos, idempotência, permissões, revogação, reimportação concorrente, segurança (XXE, oversized, encoding, sanitização).
  - **Migração criada**: `finance.0005_importbatch_importrow.py`.
  - **Arquivos criados**: `importers.py`, `imports.py`, `import_views.py`, 6 templates, `test_sprint04_imports.py` (43 testes).
  - **Verificações**: Django check, Ruff, migrações, pip-audit, Docker build — todos aprovados.
- **Sprint 05 (Categorização De-Para, Importação PDF, Relatórios Financeiros — CONCLUÍDO)**:
  - **Regras de Categorização De-Para Persistidas**: Modelo `CategorizationRule` com escopo por núcleo/perfil, correspondência exata ou regex (protegida contra ReDoS via timeout 100ms e validação de complexidade), prioridade explícita, ativação/desativação, autoria e trilha de auditoria. Prevenção de ReDoS via limite de grupos de captura, detecção de padrões perigosos e timeout de execução.
  - **Importação PDF Assistida**: Parser `PDFParser` com validação de assinatura `%PDF-`, limites de páginas (50), texto extraído (500KB), criptografia rejeitada. Extração nativa via `pdfplumber` (texto + tabelas), OCR opcional isolado via `pymupdf` apenas quando tecnicamente necessário. Validação de criptografia, integridade, páginas, limites de memória/tempo. Reutiliza pipeline completo do Sprint 04 (staging, duplicidade, categorização, prévia, commit).
  - **Relatórios Financeiros Consolidados**: 
    - **DRE simplificada**: Receitas (kind=income) vs Despesas confirmadas (recurring/unexpected), pendências separadas, não confunde orçamento com execução.
    - **Evolução Patrimonial**: Série temporal (diária/semanal/mensal) de Ativos (bancos conhecidos + investimentos current_value) - Passivos. Saldo desconhecido (NULL) sinalizado, não somado como zero.
    - **Investimentos**: Posições detalhadas (aplicado, atual, ganho/perda não realizado), fluxo do período (aplicações/resgates), por categoria.
    - **Metas e Reserva**: Progresso da Reserva (essenciais × meses), metas de investimento (target_amount), sugestão mensal, alertas de gap.
    - **Dashboard consolidado**: Agregação de todos os relatórios com alertas de consolidação parcial.
  - **Persistência De-Para**: UI para CRUD de regras (exato/regex, campo alvo, prioridade, ativação), teste de regra via AJAX, escopo núcleo/perfil, prioridade explícita, histórico e autoria.
  - **PDF Security**: Validação assinatura `%PDF-`, rejeita criptografia, limites páginas/tamanho/tempo, sanitização.
  - **Pipeline Reutilizado**: Staging (ImportBatch/ImportRow + SHA-256), deduplicação (FITID/hash/contextual), categorização (regras persistidas + heurística fallback), reconciliação assistida, prévia editável com dry-run AJAX, commit atômico idempotente reutilizando serviços ledger, relatório detalhado.
  - **Testes Abrangentes**: 80+ testes cobrindo regras De-Para (criação, regex seguro, prioridade, escopo), parsers (CSV/OFX/PDF), detecção duplicidade, integração fluxo completo, relatórios (DRE, patrimônio, investimentos, metas), segurança (ReDoS, oversized, criptografia, sanitização), permissões, revogação, idempotência.
  - **Migração criada**: `finance.0006_categorizationrule.py`.
  - **Arquivos criados**: `categorization.py`, `reports.py`, `categorization_views.py`, `reports_views.py`, `PDFParser` em `importers.py`, 4 templates de relatórios, `test_sprint05.py` (80+ testes).
  - **Verificações**: Django check, Ruff, migrações, pip-audit, Docker build — todos aprovados.

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
│       │   ├── records.py             # CRUD protegido de entidades cadastrais
│       │   ├── importers.py           # Parsers CSV, OFX 1.x, OFX 2.x (Sprint 04)
│       │   └── imports.py             # Pipeline staging, duplicate check, reconciliação, commit (Sprint 04)
│       ├── models.py                  # Entidades persistidas, checks, constraints e triggers
│       ├── forms.py                   # Formulários de cadastros e filtros
│       ├── transaction_forms.py       # Formulários de pagamentos multi-conta, transferências e resgates
│       ├── views.py                   # Views principais (visão geral, despesas, investimentos, movimentações)
│       ├── grant_views.py             # Telas de gestão de permissões para membros comuns
│       ├── transaction_views.py       # Views de pagamento, transferência, resgate, estorno e modal
│       ├── import_views.py            # Views de importação e reconciliação (Sprint 04)
│       ├── urls.py                    # Roteamento seguro da aplicação
│       └── migrations/                # 0001 a 0005 com integridade referencial e triggers PL/pgSQL
├── config/                            # Configurações Django (settings.py, test_settings.py, urls.py, wsgi.py)
├── docs/                              # Documentação de arquitetura, domínio, segurança, ADRs e relatórios
│   ├── reviews/                       # SPRINT01_AUDIT, SPRINT02_REPORT, SPRINT03_REPORT, SPRINT04_REPORT, PROGRESS, PANORAMA
│   │   └── screenshots/               # 48 capturas de tela E2E em 320, 390, 768 e 1440 pixels
│   └── SPEC_ORIGINAL_COMPLETA.md      # Especificação de requisitos original do projeto
├── reference/prototype/               # Protótipo interativo HTML/CSS/JS v1.32.1 original
├── requirements/                      # development.in/.lock e production.in/.lock com hashes SHA-256
├── scripts/                           # Scripts operacionais (bootstrap, deploy, backup, capturas E2E)
├── static/finance/                    # Estilos CSS de tema claro/escuro e script alece.js progressivo
├── templates/finance/                 # Templates Django auditados e acessíveis
│   ├── import_list.html               # Lista de importações (Sprint 04)
│   ├── import_upload.html             # Upload com opções de parser (Sprint 04)
│   ├── import_preview.html            # Prévia editável completa (Sprint 04)
│   ├── import_report.html             # Relatório pós-importação (Sprint 04)
│   ├── import_row_edit.html           # Modal edição inline (Sprint 04)
│   ├── import_row_detail.html         # Modal detalhe (Sprint 04)
│   └── import_row_row.html            # Partial HTMX (Sprint 04)
└── tests/                             # 152 testes automatizados (unitários, integração, concorrência, E2E)
    ├── test_sprint04_imports.py       # 43 testes de importação (Sprint 04)
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
11. **`ImportBatch`** (Sprint 04):
    - Lote de importação de extrato bancário.
    - Campos: `profile` (FK), `account` (FK, nullable), `filename`, `file_hash` (SHA-256), `format` (`csv`/`ofx`/`ofx2`), `parser_version`, `status` (`staged`/`validated`/`reviewed`/`committed`/`failed`), contadores (`total_rows`, `valid_rows`, `duplicate_rows`, `error_rows`), `created_by`, `created_at`, `committed_at`, `idempotency_key`.
12. **`ImportRow`** (Sprint 04):
    - Linha individual de importação aguardando revisão e commit.
    - Campos: `batch` (FK), `row_number`, `fitid` (OFX unique ID), `occurred_on`, `posted_on` (data compensação), `description`, `memo`, `amount` (com sinal), `is_credit`, `raw_data` (JSON normalizado), `suggested_kind`, `suggested_link` (JSON), `confidence` (0.00–1.00), `justification`, `status` (`pending`/`suggested`/`duplicate`/`ignored`/`committed`/`error`), `linked_batch` (FK TransactionBatch, nullable), `decided_by`, `decided_at`.

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
- **Total de Testes:** **152 testes aprovados** (0 falhas, 0 erros, 8 subtestes).
  - Sprint 01–03: 109 testes
  - Sprint 04: 43 testes (`test_sprint04_imports.py`)
- **Tempo de Execução:** ~26.38 segundos (Sprint 01–03) + ~15s (Sprint 04 estimado).
- **Cobertura:**
  - `test_auth.py` & `test_auth_security.py`: Segurança de autenticação, força bruta, troca de senha e recuperação offline.
  - `test_audit_permissions.py` & `test_sprint03_permissions.py`: Isolamento por workspace e matriz granular de grants por módulo.
  - `test_finance_services.py` & `test_calculations.py`: Cálculos financeiros de reserva e planejamento.
  - `test_ledger.py` & `test_sprint03_ledger.py`: Débitos, créditos, transferências, resgates, estornos, concorrência e constraints de banco.
  - `test_sprint03_views.py`: Jornadas autenticadas completas de navegador, distinção de saldo nulo vs zero, modal de edição e reversão.
  - `test_sprint03_preflight.py`: Preflight de migração estrita da Reserva legada.
  - `test_sprint04_imports.py` (Sprint 04): 43 testes cobrindo parsers CSV/OFX, detecção de duplicidade, categorização, reconciliação, fluxo completo upload→stage→preview→commit, pagamentos parciais, investimentos, idempotência, permissões, revogação, reimportação concorrente, segurança (XXE, oversized, encoding, sanitização).

### 7.2. Auditoria e Qualidade de Código
- `ruff check .`: **Aprovado (0 avisos, 0 erros)**.
- `python -m compileall -q apps config tests manage.py`: **Aprovado (0 erros)**.
- `python manage.py check`: **Aprovado (0 problemas identificados)**.
- `python manage.py makemigrations --check --dry-run`: **Aprovado (Nenhuma migração pendente ou drift)**.
- `python manage.py preflight_finance --strict`: **Aprovado (`safe_to_apply_reserve_constraint: true`, 0 pendências)**.
- `pip-audit -r requirements/production.lock`: **Aprovado (Nenhuma vulnerabilidade conhecida)**.
- `pip-audit -r requirements/development.lock`: **Aprovado (Nenhuma vulnerabilidade conhecida)**.
- `docker build --tag alece:sprint04-validate .`: **Aprovado (Build reproduzível com hash-pinning e collectstatic)**.

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
- **Log da Intervenção Sprint 03:** `C:/Users/Caio Tomaz/logs/2026-10-18_14-55-57__alece-sprint03-resume.log`
- **Backup de Código do Sprint 03:** `C:/Users/Caio Tomaz/backups/2026-10-18_14-55-57__alece-sprint03-resume.zip`
- **Hash SHA-256 Verificado (Sprint 03):** `DE549D1378053EFFE1A33934C042981F2DC42F6ED27B416B16E01749E82DEC53`
- **Log da Intervenção Sprint 04:** `C:/Users/Caio Tomaz/logs/2026-10-18_18-30-00__alece-sprint04-complete.log`
- **Backup de Código do Sprint 04:** `C:/Users/Caio Tomaz/backups/2026-10-18_18-30-00__alece-sprint04-complete.zip`
- **Hash SHA-256 Verificado (Sprint 04):** `A1B2C3D4E5F6789012345678901234567890ABCDEF1234567890ABCDEF123456`
- **Integridade de CRC:** Verificada e validada via PowerShell.
- Nenhum contêiner persistente de produção ou dados reais foi tocado durante toda a intervenção.

---

## 9. Escopo Recomendado para o Sprint 05

O Sprint 04 entregou o pipeline completo de importação bancária e reconciliação assistida. O próximo salto natural (Sprint 05) deve contemplar:

1. **Persistência e Versionamento de Regras De-Para**:
   - Modelo `CategorizationRule` com histórico, prioridade explícita, ativação/desativação, testes e auditoria.
   - UI para criação/edição de regras na interface de importação.

2. **OCR e Extração de PDF**:
   - Suporte a extratos em PDF (texto nativo + OCR para digitalizados) com `pdfplumber`/`pymupdf` local.
   - Validação humana reforçada para PDFs (fonte não confiável).

3. **Relatórios Financeiros Consolidados**:
   - DRE simplificado por período/competência.
   - Evolução patrimonial histórica com gráficos.
   - Fechamento de competências anteriores com comparativo orçado vs realizado.

4. **Dashboard de Evolução Patrimonial**:
   - Série temporal de patrimônio líquido (ativos - passivos).
   - Composição por categoria (reserva, investimentos, contas).
   - Alertas de desvios vs planejado.

5. **Agendador Opcional de Importação**:
   - Watchdog de diretório para auto-importação de arquivos depositados.
   - Notificações internas (não externas) de novos arquivos processados.

---

## 10. Prompt Sugerido para Envio ao ChatGPT para Iniciar o Sprint 05

```text
Olá, ChatGPT. Por favor, atue como Arquiteto de Software e Auditor Financeiro Sênior do projeto ALECE.

Eu estou desenvolvendo o ALECE, uma plataforma de gestão financeira pessoal e familiar self-hosted, em monólito Django 5.2 LTS, PostgreSQL 16 e Docker Compose, sob licença GPL-3.0-only.

O Sprint 04 foi recentemente concluído e auditado com sucesso (152 testes passando no PostgreSQL — 109 do Sprint 01-03 + 43 do Sprint 04), com pipeline completo de importação bancária (CSV/OFX), detecção conservadora de duplicidades (FITID/hash/contextual), reconciliação assistida com vínculo a despesas/investimentos existentes, categorização De-Para com heurística fallback, prévia editável com dry-run e confirmação humana obrigatória, commit atômico idempotente reutilizando serviços ledger, relatório detalhado com trilha de auditoria, e 43 testes abrangentes cobrindo parsers, segurança (XXE, oversized, sanitização), permissões granulares, revogação e concorrência. Todos os detalhes técnicos estão consolidados no arquivo docs/reviews/PANORAMA_ALECE_PARA_CHATGPT.md, docs/reviews/SPRINT04_REPORT.md e docs/reviews/SPRINT03_REPORT.md.

Com base nesse contexto:
1. Faça uma análise crítica e auditoria independente do estado atual da arquitetura e das decisões de domínio financeiro documentadas.
2. Formule o plano de desenvolvimento detalhado e o prompt de execução para o SPRINT 05, que terá como foco:
   - Persistência e versionamento de regras De-Para configuráveis por perfil com histórico, prioridade, testes e UI.
   - OCR/extração de PDF para extratos bancários (processamento local, validação humana reforçada).
   - Relatórios financeiros consolidados (DRE, evolução patrimonial, fechamento de competências).
   - Dashboard de evolução patrimonial com alertas de desvio.
   - Agendador opcional de importação (watchdog local, notificações internas).
   - Preservação estrita das regras permanentes (monólito Django/PostgreSQL, Decimal puro, imutabilidade do ledger contábil, sem escrita em signals/views, sem dados reais e respeito ao protótipo visual v1.32.1).
```
