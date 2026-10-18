# Changelog

## 0.7.0 (Sprint 05 — Categorização De-Para, Importação PDF, Relatórios Financeiros) — 2026-10-18

- **Regras de Categorização De-Para Persistidas**: Modelo `CategorizationRule` com escopo por núcleo/perfil, correspondência exata ou regex (protegida contra ReDoS via timeout 100ms e validação de complexidade), prioridade explícita, ativação/desativação, autoria e trilha de auditoria. Prevenção de ReDoS via limite de grupos de captura, detecção de padrões perigosos e timeout de execução.
- **Importação PDF Assistida**: Parser `PDFParser` com validação de assinatura `%PDF-`, limites de páginas (50), texto extraído (500KB), criptografia rejeitada. Extração nativa via `pdfplumber` (texto + tabelas), OCR opcional isolado via `pymupdf` apenas quando tecnicamente necessário. Validação de criptografia, integridade, páginas, limites de memória/tempo. Reutiliza pipeline completo do Sprint 04 (staging, duplicidade, categorização, prévia, commit).
- **Relatórios Financeiros Consolidados**: 
  - **DRE simplificada**: Receitas (kind=income) vs Despesas confirmadas (recurring/unexpected), pendências separadas, não confunde orçamento com execução.
  - **Evolução Patrimonial**: Série temporal (diária/semanal/mensal) de Ativos (bancos conhecidos + investimentos current_value) - Passivos. Saldo desconhecido (NULL) sinalizado, não somado como zero.
  - **Investimentos**: Posições detalhadas (aplicado, atual, ganho/perda não realizado), fluxo do período (aplicações/resgates), por categoria.
  - **Metas e Reserva**: Progresso da Reserva (essenciais × meses), metas de investimento (target_amount), sugestão mensal, alertas de gap.
  - **Dashboard consolidado**: Agregação de todos os relatórios com alertas de consolidação parcial.
- **Persistência De-Para**: UI para CRUD de regras (exato/regex, campo alvo, prioridade, ativação), teste de regra via AJAX, escopo núcleo/perfil, prioridade explícita, histórico e autoria.
- **PDF Security**: Validação assinatura `%PDF-`, rejeição criptografia sem senha, limites páginas/tamanho/tempo, sanitização texto, proteção path traversal.
- **Pipeline Reutilizado**: Staging (ImportBatch/ImportRow + SHA-256), deduplicação (FITID/hash/contextual), categorização (regras persistidas + heurística fallback), reconciliação assistida, prévia editável com dry-run AJAX, commit atômico idempotente reutilizando serviços ledger, relatório detalhado.
- **Testes Abrangentes**: 80+ testes cobrindo regras De-Para (criação, regex seguro, prioridade, escopo), parsers (CSV/OFX/PDF), detecção duplicidade, integração fluxo completo, relatórios (DRE, patrimônio, investimentos, metas), segurança (ReDoS, oversized, criptografia, sanitização), permissões, revogação, idempotência.
- **Verificações**: Django check, Ruff, migrações, pip-audit, Docker build — todos aprovados.

## 0.6.0 (Sprint 04 — Importação Bancária e Reconciliação Assistida) — 2026-10-18

- **Pipeline de Importação Modular**: Adaptadores versionados para CSV (UTF-8, ISO-8859-1, Windows-1252; delimitadores `;`, `,`, tab, `|`; cabeçalho opcional; colunas crédito/débito separadas ou valor único com sinal), OFX 1.x (SGML) e OFX 2.x (XML com proteção XXE e expansão de entidades). Parser factory com detecção automática de formato por extensão e conteúdo.
- **Segurança de Upload**: Validação de tamanho (5 MiB), tipo, codificação, estrutura e limites (5.000 linhas). Sanitização de textos contra XSS, formula injection, caracteres de controle. Processamento 100% local (self-hosted), sem transmissão a terceiros.
- **Staging e Auditoria**: Modelos `ImportBatch` e `ImportRow` com hash SHA-256 do arquivo, versão do parser, contadores de linhas válidas/duplicadas/erros, status de processamento (`staged`, `validated`, `reviewed`, `committed`, `failed`), trilha de auditoria completa (autor, timestamps, idempotency key).
- **Detecção Conservadora de Duplicidades**: Prioridade 1) FITID (identificador bancário único), 2) Hash do arquivo (reimportação idêntica), 3) Comparação contextual (data ±1 dia, valor exato em centavos, similaridade de descrição por palavras-chave >3 chars). **Não presume duplicidade** por apenas mesmo valor/data — sinaliza revisão e preserva lançamentos legítimos.
- **Reconciliação Assistida**: Sugestões inteligentes por linha: vincular a despesa previsível/imprevisível existente (com detecção de pagamento parcial via `MonthlyExpense`), aplicação/resgate em investimento, transferência entre contas, recebimento, nova despesa imprevisível. Alertas de conflito (valor acima do devido, conta sem saldo) e justificativa textual para cada sugestão.
- **Categorização De-Para Configurável**: Regras por perfil com padrão (regex ou termo exato), campo alvo (descrição/memo/ambos), tipo sugerido, vínculo sugerido, prioridade explícita, ativação/desativação, histórico. Heurística de fallback para transações sem regra.
- **Prévia Editável Integrada**: Interface alinhada ao protótipo v1.32.1 (temas Claro/Escuro, sidebar, lápis por linha, modal com ações no rodapé). Seleção individual de linhas, indicação visual de duplicidades, edição de valor/descrição/tipo/competência/conta, splits multi-conta, ações em massa, dry-run via AJAX, confirmação humana obrigatória via POST com chave idempotente.
- **Commit Atômico e Idempotente**: Transação PostgreSQL única criando/vinculando `TransactionBatch` com ledger balanceado (partidas dobradas), atualizando saldos e posições via `select_for_update()`. Idempotência por `idempotency_key` no batch e por linha. Estorno de importação via `reverse_batch` existente.
- **Relatório Detalhado Pós-Importação**: Resumo (inseridos, vinculados, ignorados, duplicados, erros), lista de `TransactionBatch` criados, trilha de auditoria (hash arquivo, parser, autor, timestamp, chave idempotente), avisos de conflitos.
- **Permissões Granulares**: Requer `accounts:edit` e `movements:edit` no perfil alvo. Administrador acessa todos os perfis; usuário comum depende de `ProfileGrant` explícito. Revogação imediata no próximo request.
- **Testes Abrangentes**: Unitários (parsers CSV/OFX, detecção duplicidade, categorização, reconciliação), integração (fluxo completo upload→stage→preview→commit, pagamentos parciais, investimentos, idempotência, permissões, revogação, reimportação concorrente), segurança (XXE, oversized, encoding, sanitização, path traversal).

## 0.5.0 (Sprint 03 — Transações, Movimentações, Pagamentos e Permissões Granulares) — 2026-10-18

- **Ledger e Trilha de Auditoria**: Implementação de partidas dobradas (`JournalEntry`), lotes de transação (`TransactionBatch`) e pernas bancárias (`LedgerLeg`). Invariantes de balanço e imutabilidade auditável estrita assegurados por triggers e constraints no PostgreSQL (`finance_assert_journal_balance`, `finance_guard_posted_history`).
- **Pagamentos e Saídas**: Pagamento parcial e dividido entre múltiplas contas (`confirm_outflow`), validação de saldo disponível, idempotência via chave única e prevenção rigorosa de saldo negativo e dupla contabilização.
- **Competências Mensais**: Criação de `MonthlyExpense` e `MonthlyInvestmentPlan` com controle de quitação parcial, total e histórico por competência.
- **Estornos e Reversões**: Estorno atômico e simétrico (`reverse_batch`), preservando o histórico integral do ledger, revertendo lançamentos contábeis e ajustando saldos e posições financeiras sem perda de dados.
- **Transferências e Resgates**: Transferência entre contas com contas de partida e contrapartida sem classificação indevida de receita/despesa (`transfer`), e resgate de investimentos com baixa proporcional do custo de aquisição e atualização do saldo líquido (`withdraw_investment`).
- **Permissões Granulares por Módulo**: `ProfileGrant` estendido com níveis `none`, `view`, `edit` independentes para cada um dos 5 módulos (`overview`, `accounts`, `expenses`, `investments`, `movements`), validadas sob demanda e com revogação imediata no próximo request. Administradores acessam todos os perfis do núcleo.
- **Ajustes de Integridade Financeira e UI**:
  - Distinção rigorosa entre saldo bancário totalmente desconhecido (`NULL`), saldo conhecido igual a zero (`0.00`) e projeção parcial em Visão Geral e Resumos.
  - Substituição do botão direto de estorno pelo lápis de ação por linha no histórico de movimentações, integrando o estorno ao modal de edição de movimentação (`movement-detail`) do protótipo v1.32.1.
- **Qualidade, Regressão e Verificações**: Suíte ampliada para 109 testes aprovados no PostgreSQL efêmero com concorrência e multithreading; auditoria `pip-audit` limpa para produção e desenvolvimento; build de imagem Docker com hash-pinning; e captura de evidências visuais E2E em 320, 390, 768 e 1440 pixels para ambos os temas Claro e Escuro.

## 0.4.0 — 2026-10-18

- Auditoria do Sprint 01 em PostgreSQL isolado, com correção da emissão anônima de recuperação, proteção contra replay e força bruta, validação de senha e redirecionamento de login.
- Admin de workspace acessa todos os perfis do próprio núcleo; grants para usuários comuns são verificados por workspace. Escrita financeira direta pelo Django Admin bloqueada.
- Sprint 02: perfis ativos/arquivados, renda ausente/zero/positiva, contas com saldo conhecido/desconhecido, despesas previsíveis e imprevisíveis, posições de investimento, Reserva e consultas isoladas por mês/perfil.
- Ações de cadastro, edição, arquivamento e exclusão autorizadas por objeto, via serviços transacionais. Cadastros de renda, despesas e investimento não criam movimentações bancárias.
- Visão geral, Despesas, Investimentos, seletor de perfis, formulários com melhoria progressiva, tema Claro/Escuro e adaptação a mobile. Migração `finance.0002_sprint02_catalogs` adiciona arquivamento, data opcional da posição e checks de vencimento e meta da Reserva.
- Pipeline de publicação exige acionamento manual explícito em tag versionada. CI audita dependências de produção; a imagem local atualiza o instalador `pip` antes de instalar a aplicação.

## 0.3.0 — 2026-10-18

- Primeiro fluxo financeiro após login: seleção de núcleo, listagem e criação de perfis financeiros, consulta e criação de contas bancárias ou dinheiro físico por perfil.
- Criação de perfis restrita a administradores do núcleo, com limite de cinco aplicado pelo serviço transacional e grant de visualização/edição para o criador.
- Visualização e criação de contas protegidas por grants; vínculos de permissão entre núcleos diferentes são ignorados. Acesso de administrador aos perfis do seu núcleo é implementado na auditoria do Sprint 01.
- Formulários com validação de nomes duplicados, valores não negativos e distinção entre renda/saldo desconhecido e zero informado; navegação, estados vazios e mensagens em português.
- Testes do fluxo autenticado, autorização, isolamento, validação e limite. Modelos existentes reutilizados, sem nova migration.

## 0.2.0 — 2026-10-15

### Fase 1 — Autenticação, Usuários, Workspaces, Perfis Financeiros e Permissões

- **Autenticação Django**: Login, logout, alteração de senha com views personalizadas e templates consistentes com o design system ALECE.
- **Recuperação offline**: Código de recuperação único (SHA-256 hash, uso único, sem e-mail) para redefinição de senha.
- **Modelo UserProfile**: Campos estendidos para recovery code, preferência de tema (light/dark/auto).
- **Sistema de permissões granular** (`apps.core.permissions`):
  - Isolamento por workspace (núcleo familiar) via `WorkspaceMembership` (roles: admin/common).
  - Isolamento por perfil financeiro via `ProfileGrant` (can_view, can_edit).
  - Funções de verificação: `user_can_view_profile`, `user_can_edit_profile`, `get_accessible_profiles`, `get_editable_profiles`.
  - Decorators/guards: `require_profile_view`, `require_profile_edit`, `require_workspace_admin`.
  - Filtro de queryset por acesso do usuário: `filter_queryset_by_user_access`.
- **Home page protegida**: `@login_required` na view principal, redirecionamento para login customizado.
- **Configuração de URLs**: `LOGIN_URL = "login"`, `LOGIN_REDIRECT_URL = "home"`, `LOGOUT_REDIRECT_URL = "login"`.
- **Testes abrangentes**: 26 novos testes de autenticação, recuperação e permissões (total 40 testes passando).
- **Documentação**: Atualização do CHANGELOG e README.

## 0.1.0 — 2026-10-15

- Starter de engenharia organizado em monólito modular Django.
- PostgreSQL + Compose + Gunicorn + healthchecks.
- Modelos financeiros iniciais, reserva 9 meses, cálculo decimal e serviço de débito multi-conta.
- GitHub Actions CI / publicação de imagem em tags, Dependabot e documentação operacional.
- Protótipo visual v1.32.1 e especificação original preservados como referência sem integração.

**Não é release funcional do aplicativo ALECE completo.**
