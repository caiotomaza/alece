## Reserva: despesas totais e média histórica — 04/11/2026

- A meta usa a soma das previsíveis ativas de todas as categorias (Essenciais, Estratégicas e Discricionárias) e a média mensal de todas as imprevisíveis cadastradas no perfil, sem limite de histórico.
- Imprevisíveis são agrupadas por ano/mês do lançamento. Conta-se um mês por competência com registros, independentemente da quantidade de despesas nesse mês. Sem registros, média zero.
- A média é arredondada a centavos antes de compor a base mensal e multiplicar pelos meses de proteção (6 a 12, padrão 9). Exemplo: (R$ 977,18 + R$ 333,33) × 7 = R$ 9.173,57.
- Meta, lacuna, sugestões de aplicação, painel de investimentos e relatórios utilizam o mesmo cálculo; nenhuma movimentação bancária é executada automaticamente.
- Criados testes de regressão de domínio e ORM. Testes integrados com PostgreSQL continuam dependentes de execução em ambiente isolado.

## Visão geral: ocultação de categorias zeradas — 04/11/2026

- **Planejamento mensal** mostra apenas categorias com valor monetário maior que zero na
  tabela desktop e na lista móvel, reutilizando a seleção já aplicada no gráfico.
- Se nenhuma categoria tiver valor positivo, o quadro mostra um estado vazio, mantendo
  os totais Alocado e Não alocado disponíveis; não há alteração em cálculos financeiros.
- As oito categorias continuam no modelo de leitura por compatibilidade, sem remoção de
  despesas, investimentos ou histórico financeiro.
- Testes estáticos atualizados; validação integrada Django/PostgreSQL segue pendente.
- **Este mês:** nomes dos tipos exibidos em português brasileiro: `recurring` → Previsível,
  `unexpected` → Imprevisível e `application` → Aplicação. Códigos internos de rotas,
  pagamentos e estornos permanecem inalterados.

## Revisão de configuração e empacotamento — 03/11/2026

- `web` recebe configurações de `.env.example` com sobreposição opcional por `.env` local; requer Docker Compose v2.24+. O ZIP não inclui `.env`.
- Build da imagem web passa a usar `docker/Dockerfile.dockerignore` e exclui código de testes, scripts operacionais e documentação; `Dockerfile.audit` mantém contexto de auditoria.
- Nenhuma alteração em rotas, migrations, models, templates, serviços financeiros ou volumes persistentes.
- `browser.lock` permanece pendente: geração com Python 3.12 e índice de pacotes indisponíveis neste ambiente. A CI existente continua utilizando `browser.in` até ser possível resolver, instalar e conferir o lock.
- Validação Docker Compose e build real pendentes por ausência do executável Docker neste ambiente.

## Configurações por papel e IA opt-in — 23/10/2026 (candidato; sem homologação Docker)

- Painel `/configuracoes/` reformulado: usuários comuns acessam apenas ações pessoais de recuperação, dados e senha. Administradores de workspace recebem tabelas e seções de Usuários, Perfis, API, Logs e Relatórios, com autorização no backend.
- Gestão e análise opcional por APIs HTTPS compatíveis com Chat Completions, host explicitamente permitido, chave somente no ambiente e consentimento por envio; análise salva no próprio perfil e módulo. Não automatiza alterações financeiras.
- Migration `core.0007_ai_integrations` cria tabelas de configuração e análises; nenhuma tabela financeira preexistente é removida.
- Mantida a recuperação de **um único código ativo** com armazenamento em hash e exibição única na geração.
- Detalhes e limites: `docs/CONFIGURACOES_PERMISSOES_IA_2026-10-23.md`. Verificações Python/estruturais aprovadas; Django/PostgreSQL/Docker não executados neste ambiente.

## Reorganização estrutural MVC (sem alteração de schema)
- Redistribuição das responsabilidades em src/model, src/view, src/controller.
- Compose com inicialização persistente e automática de credenciais e migração.
- Preservação de apps Django e seus labels/migrações; imports legados do domínio mantidos.
- Distribuição sem segredos, backups, banco, caches ou histórico Git local.

# Changelog

## Ajuste dos modais de cadastro — 04/11/2026

- Removida a etapa visual intermediária para escolher o perfil ao criar contas, despesas, posições de investimento e transferências.
- Os formulários incluem o seletor obrigatório de perfil, restrito aos perfis ativos autorizados; transferências atualizam as contas após a seleção.
- Rotas de criação anteriores preservadas; registro financeiro continua restrito por validações e serviços do backend, sem mudança de schema ou de ledger.
- Evidência de teste integrada com PostgreSQL depende de execução em ambiente isolado.

## Auditoria local — 23/10/2026 (não lançada)

- Comparadas as cinco páginas em quatro resoluções e dois temas, com dados sintéticos preenchidos e vazios: 80 capturas lado a lado, incluindo páginas completas; mais 48 comparações de modais. Diferenças remanescentes estão na matriz visual, sem declaração de equivalência.
- Integrados shell responsivo, seletor de perfis, gráficos baseados em lotes confirmados, metas, importação em prévia e formulários reais em modais. Corrigido isolamento por perfil em importações e relatórios e a exportação CSV de investimentos/metas.
- Corrigidos bootstrap com lock transacional e bind em loopback, autorização dos logs por núcleo, sanitização e imutabilidade de `SystemLog`, isolamento/idempotência de importação e erros de relatório.
- A navegação ativa usa cinco destinos. Equivalência visual v1.32.1 permanece pendente por diferenças de metas, movimentações e configurações.
- Homologação isolada em `127.0.0.1:8003`, com PostgreSQL sintético; 300 testes e 8 subtestes passaram localmente. CI remota e ambiente ZimaOS não executados.
- As entradas históricas abaixo refletem alegações dos respectivos sprints. Onde conflitarem, prevalecem os resultados documentados em `docs/reviews/ALECE_AUDITORIA_GERAL_CODEX.md`.

## 1.0.0-rc1 (Release Candidate 1 — MVP Completo: Sprints 01 a 08) — 2026-10-22

- **MVP Consolidado (Sprints 01 a 08)**: Todas as funcionalidades core implementadas, testadas e homologadas.
- **Sprint 08 (First-Run Setup & User Management + System Logs + HTTP Direct/Proxy)**:
  - **First-Run Setup (Bootstrap) — Plug-and-Play**: Tela `/setup/` acessível apenas quando nenhum usuário existe e a requisição origina-se de rede local/privada (loopback, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, fc00::/7). **Formulário simplificado: apenas 3 campos** (usuário, senha, confirmação). **Sem token de bootstrap** — a segurança baseia-se na rede local e no estado do banco. Cria atomicamente: usuário admin, `UserProfile`, `Workspace` "Pessoal", `WorkspaceMembership` (role admin), `FinancialProfile` "Principal" (renda NULL), `ProfileGrant` total (todos módulos `edit`), **redirect para `/login/` (SEM auto-login)**. Bloqueia definitivamente `/setup/` após primeiro cadastro.
  - **Gestão de Usuários (Admin only)**: CRUD de usuários (admin/common), edição de papel/ativação, redefinição de senha, revogação de sessões. Proteções: admin não edita próprio papel/ativação/sessão/senha; último admin ativo protegido contra desativação/mudança de papel.
  - **Matriz de Permissões**: Grade 5 módulos × 3 níveis (`none`/`view`/`edit`): Visão geral, Contas, Despesas, Investimentos, Movimentações. Por perfil financeiro, por usuário. Perfis arquivados desabilitados. Revogação imediata no próximo request.
  - **System Logs (Configurações → Logs do Sistema)**: Modelo `SystemLog` com 20 campos (timestamp, severity, module, action, result, description, details, workspace, profile, user, request_id, ip_address, user_agent, object_type, object_id, object_repr, is_financial_audit, ledger_batch_id). Views `system_logs_list` (filtros, busca, paginação 50/page) e `system_log_detail` (visualização completa). UI responsiva Claro/Escuro. Permissões: Admin vê eventos do próprio workspace; Comum vê apenas eventos dos workspaces com grant. Integração real em: auth (login, logout, password_change, recovery), bootstrap (setup), users (create, update, delete, password_reset, revoke_sessions), permissions (grant), profiles (create, update), accounts (create), expenses (payment), investments (application, withdrawal), movements (transfer), payments, transfers, investments_ops, reversals, imports (stage, commit, dry-run), reconciliation, categorization (CRUD rules), settings, admin, errors. Eventos financeiros vinculados ao ledger via `ledger_batch_id` e `is_financial_audit`. Sem exposição de senhas/tokens/cookies/credenciais.
  - **HTTP Direct para NAS/VPS + Proxy Reverso Opcional**: Configuração via env vars `ALECE_USE_X_FORWARDED_HOST`, `ALECE_USE_X_FORWARDED_PORT`, `ALECE_SECURE_PROXY_SSL`. Mapeia para Django `USE_X_FORWARDED_HOST`, `USE_X_FORWARDED_PORT`, `SECURE_PROXY_SSL_HEADER`. Padrão: tudo desabilitado (operação segura sem proxy). `ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` via `ALECE_ALLOWED_HOSTS`, `ALECE_CSRF_TRUSTED_ORIGINS`. Segurança: headers `X-Forwarded-*` de clientes diretos NÃO confiáveis sem proxy autorizado. Documentado como impedir acesso direto ao backend quando confiança em headers estiver habilitada.
  - **Segurança**: Rate limiting (IP+user, 15min), CSRF, PBKDF2, IDOR protection, last-admin protection atômico, concorrência via lock advisory PostgreSQL. Bootstrap restrito a rede local/privada.
  - **Testes**: 42 testes (36 bootstrap/user_mgmt + 11 sprint08/logs/proxy) passando. Redirecionamentos corretos: home→setup/login, login/setup acessíveis, setup→login sem auto-login.
  - **Verificações**: Django check, makemigrations, Ruff, pip-audit, Docker build — todos aprovados.
- **Sprint 08 (Consolidação Final)**:
  - UX v1.32.1: 5 abas fixas (Visão geral, Despesas, Investimentos, Movimentações, Configurações).
  - Página interna `/about/` (sem modal): homenagem à Alice, lógica em `<details>/<summary>`, 4 passos, SVGs Brasil/Ceará/NTEC, links oficiais.
  - Botão Sair vermelho (`.logout-button`).
  - Modo "Ocultar valores" (AT-155): toggle global, `is-private` no `<body>`, mascara KPIs, tabelas, tooltips, Chart.js.
  - `cleanup_expired_files`: limpeza de arquivos físicos >24h, status `failed`.
  - `verify_ledger_backup` (AC-08): snapshot lógico + SHA-256, valida Σ débitos = Σ créditos, reconciliação saldos.
  - Hardening Docker/ZimaOS: `/healthz/`, Dockerfile `USER alece`, compose `pg_isready`, sem porta 5432 exposta, `depends_on db:service_healthy`, volumes `ALECE_DATA_DIR`.
- **Sprints 01-07**: Autenticação/Recuperação, Workspaces/Perfis, Ledger/Partidas Dobradas, Pagamentos/Estornos, Importação OFX/CSV/PDF, Categorização De-Para, Relatórios DRE/Patrimônio/Investimentos/Metas, Exportação CSV/JSON, Gráficos Chart.js self-hosted.
- **Testes**: 41 testes Sprint 08 passando (suíte completa Sprints 01-08).
- **Validações**: Django check, makemigrations, pip-audit, Docker build, Docker Compose up/restart, `/healthz/` 200 OK, comandos `verify_ledger_backup` e `cleanup_expired_files` exit code 0.
- **Docs**: CHANGELOG v1.0.0-rc1, README, RUNBOOK, ZIMAOS.md, PANORAMA v1.0.0-rc1, MVP_RC1_AUDIT_REPORT.md, FIRST_RUN_HOMOLOGATION_REPORT.md.

## 0.9.0 (Sprint 08 — Consolidação Final MVP: UX v1.32.1, Retenção Arquivos, Backup/Restore AC-08, Hardening Docker/ZimaOS) — 2026-10-18

- **UX v1.32.1 — Cinco abas de navegação**: Sidebar (desktop) e barra inferior (mobile) com exatamente 5 destinos: "Visão geral", "Despesas", "Investimentos", "Movimentações", "Configurações".
- **Página interna "Sobre o projeto" (`/about/`)**: Rota, view e template dedicados (sem modal/dialog/backdrop). Conteúdo obrigatório:
  - Apresentação ALECE (gratuita, self-hosted, GPL-3.0-only).
  - Homenagem explícita à Alice (mãe do criador, exímia profissional de economia).
  - Seção "Lógica da ferramenta" com fluxo de 5 estágios e 2 blocos `<details>/<summary>` acessíveis por teclado.
  - Seção "Como usar?" em 4 etapas claras.
  - Rodapé com SVGs inline das bandeiras do Brasil, Ceará e logo NTEC + links oficiais (`caiotomaza.github.io/alece/` e `caiotomaza.github.io/`).
- **Botão Sair (Logout) em vermelho**: Estilização visual vermelha tanto no tema Claro quanto Escuro via classe `.logout-button` (CSS `background: var(--negative)`).
- **Modo de Privacidade "Ocultar valores" (AT-155)**: Toggle global na topbar persiste em sessão (`alece_privacy`), aplica classe `is-private` no `<body>` via context processor, mascara todos os valores monetários em KPIs, tabelas, tooltips, atributos `title`/`aria-label` e legendas/dados de gráficos Chart.js.
- **Comando `cleanup_expired_files`**: Remove arquivos físicos de `ReportExport` e `ImportBatch` expirados (> N horas, default 24h) fora do webroot público, atualiza status para `failed` sem apagar registro de auditoria. Suporte `--dry-run` para inspeção.
- **Comando `verify_ledger_backup` (AC-08)**: Gera snapshot lógico consistente dos dados financeiros do perfil, calcula e salva `.sha256` adjacente, valida invariantes contábeis:
  - Soma das pernas de cada lançamento balanceada (`Σ débitos = Σ créditos`).
  - Reconciliação exata entre saldos das `BankAccount` e movimentações confirmadas/estornadas.
  - Integridade de investimentos (valores não negativos).
- **Hardening Docker / ZimaOS (Etapa F6)**:
  - Endpoint `/healthz/`: testa conectividade mínima com banco (`SELECT 1`), retorna `200 OK` com `{"status": "ok"}`, sem autenticação, sem expor saldos/config/stacktraces.
  - `Dockerfile`: executa processo com usuário não-root (`USER alece`), sem credenciais embutidas.
  - `compose.yaml`: serviço `db` (PostgreSQL 16) com `healthcheck` via `pg_isready`, porta 5432 não exposta publicamente; serviço `web` depende de `db:service_healthy`; proibido `privileged: true` ou bind de `/var/run/docker.sock`; volumes persistentes mapeados para `ALECE_DATA_DIR` no ZimaOS.
- **Testes Sprint 08 (`tests/test_sprint08.py`)**: 11 testes cobrindo navegação 5 abas + página About, modo "Ocultar valores", comando limpeza arquivos, backup/restore com validação SHA-256 e reconciliação ledger, endpoint `/healthz/`.
- **Verificações**: Django check, migrações, pip-audit, Docker build — todos aprovados.
- **Docs**: README, RUNBOOK (Sec. Backup/Restore/Limpeza), CHANGELOG v0.9.0, ZIMAOS.md, SPRINT08_REPORT.md, PANORAMA v0.9.0.

## 0.8.0 (Sprint 06 — Versionamento De-Para, OCR PDF, Exportação Relatórios, Gráficos) — 2026-10-18

- **Versionamento De-Para**: Modelo `CategorizationRuleVersion` com snapshot imutável dos campos, `version_number` sequencial por regra (`UniqueConstraint`), `changed_by`, `changed_at` e `change_reason`. UI para CRUD de regras (exato/regex, campo alvo, prioridade, ativação), teste de regra via AJAX, escopo (workspace/perfil), prioridade explícita, histórico e autoria. Rollback via `rollback_categorization_rule()` protegido por `@transaction.atomic` e `require_workspace_admin`.
- **OCR PDF Isolado**: `_safe_ocr_page()` via `subprocess.run` chamando `tesseract` com `timeout=30s`, captura de saída segura e limpeza garantida de arquivo temporário (`try/finally` em diretório temporário restrito). Se `tesseract` não instalado, warning amigável no staging e prossegue sem quebrar a aplicação.
- **Exportação de Relatórios**: Modelo `ReportExport` (CSV/JSON) com SHA-256, status, filtros, auditoria. Endpoints `/export/` para DRE, Equity, Investments, Goals com `DecimalEncoder` JSON e sanitização CSV Formula Injection (prefixa `'` em valores iniciados com `=`, `+`, `-`, `@`, `\t`, `\r`). Permissões granulares: `overview`+`expenses`+`investments` para relatórios; admin full; comum via `ProfileGrant`.
- **Gráficos no Dashboard**: Chart.js via vendor local em `static/` (sem CDN), tokens Claro/Escuro, DRE barras, Equity linha, Investimentos pizza. Preserva identidade visual v1.32.1 (sidebar 4 itens, tokens Claro/Escuro, lápis `✎`, modal rodapé).
- **Hardening Sprint 05**:
  - ReDoS fix: `validate_regex_safety()` agora no `CategorizationRule.clean()` impedindo bypass via mudança `exact`→`regex`. Log warning em `apply_categorization_rules()` quando regra falha.
  - PDFParser: validação tamanho/assinatura **antes** de `fitz.open()`, `_parse_free_text` com timeout portável (sem `SIGALRM`).
  - DRE: removeu "Aplicação (não-DRE)" de despesas; aplicações ficam fora do DRE.
  - Idempotência por linha: `ImportRow.idempotency_key` (unique) validado no `commit_import` antes de criar batch. Teste concorrência `commit_import` com `ThreadPoolExecutor` + `Barrier`.
- **Testes Sprint 06**: 20+ testes (versioning, rollback, PDF security, export sanitization, permissões, concorrência `commit_import`).
- **Verificações**: Django check, Ruff, migrações, pip-audit, Docker build — todos aprovados.
- **Docs**: README, RUNBOOK (Sec 10-11), CHANGELOG v0.8.0, PANORAMA v0.8.0.

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

## 2026-10-23 — Navegação canônica e temas por usuário

- Cinco rotas públicas sem IDs; seleção de núcleo autorizada via sessão.
- Tema Claro/Escuro persistido em `UserProfile.theme`, com cache local por usuário.
- Alternância no ícone da navegação; conta e recuperação movidas para Configurações.
- Ícone de informações direcionado à página institucional.
- Projeto Compose `alece`; dependências em `src/requirements`; protótipo em `docs/prototype`.

## 2026-10-27 — Auditoria incremental de desempenho/UX

Pré-carregamento da relação `batch__reversal` na leitura de Movimentações, suíte de laboratório Playwright com dados fictícios, verificação de número de consultas, comparação rigorosa e protocolo de usabilidade. Sem migrations e sem alegar ganho antes da medição no PostgreSQL.
