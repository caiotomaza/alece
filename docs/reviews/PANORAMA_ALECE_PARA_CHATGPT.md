# Panorama técnico do ALECE para revisão independente

## 1. Identificação

Projeto ALECE, versão de trabalho `0.4.0 (em desenvolvimento)`, data 2026-10-18, branch `codex/sprint01-audit-sprint02`. Commit inicial auditado: `e9e36a6e05a86626f3ac2ee77e9178fcc7676ecb`. Commit de consolidação da implementação: `a1832e69626d3c987217ed74ee6c19104d2290b`. O commit final, que também inclui este panorama e a correção visual do seletor, é o `HEAD` do checkout entregue e deve ser lido com `git rev-parse HEAD`; seu hash não pode constar no próprio conteúdo do commit. Ambiente: Windows/PowerShell com Python 3.14.8 no host; execução funcional em contêiner Python 3.12.15, Django 5.2.18, PostgreSQL 16 efêmero em `tmpfs`, Docker 29.8.2 e Compose 5.6.0. Status: Gate A aprovado; Sprint 02 aprovado **para revisão**, sem aprovação de produção. O container e o banco persistentes pré-existentes não foram usados.

## 2. Objetivo da execução

O pedido anexado exigiu auditar de forma reproduzível o Sprint 01, corrigir falhas bloqueadoras, decidir o Gate A e então desenvolver o Sprint 02: cadastros e consultas persistentes de perfis, contas/saldos, renda, despesas previsíveis e imprevisíveis, investimentos/Reserva e interface fiel ao protótipo. Foram executados esses escopos, testes, migração isolada, build local, revisão de segurança e documentação. Não foram iniciados importação CSV/PDF, integração bancária, pagamento dividido, conciliação, deploy ou migração real.

## 3. Auditoria do Sprint 01

A base `e9e36a6` tinha 40 testes, dos quais 26 métodos em `tests/test_auth.py`; um deles era um `pass` e passou a verificar 403 real. O snapshot de entrada também tinha 12 testes não commitados do primeiro fluxo de perfis/contas, total 52, aprovados em PostgreSQL antes das correções. A auditoria acrescentou testes de segurança, permissão e concorrência. Gate A final: **69 coletados, 69 aprovados, 0 reprovados, 0 ignorados**, 8 subtestes aprovados. Comandos: `pytest -q -p no:cacheprovider --tb=short`, `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `ruff check .`, migração core ida/volta, `docker build` local e `pip-audit` das dependências de produção. Todos os resultados usados no Gate foram sequenciais no PostgreSQL efêmero. Duas tentativas sobrepostas colidiram no mesmo banco de teste e **não** fundamentaram a decisão.

Achados críticos/altos corrigidos: emissão anônima de código de recuperação permitia tomada de conta; resgate concorrente podia reaproveitar código; login, admin e recuperação não tinham limite compartilhado; redefinição de senha ignorava validadores. Correções: emissão autenticada com senha atual, versão que invalida códigos legados, locks transacionais, quotas persistentes por identificador HMAC e `SetPasswordForm`. Também foram corrigidos open redirect, enumeração por mensagem, bypass de escrita financeira no Admin, grants cruzados, divergência da política do administrador do núcleo e script manual que expunha credenciais de teste. Risco residual: quotas por peer podem bloquear temporariamente usuários atrás do mesmo NAT; proteção TLS/proxy e retenção de logs dependem da implantação; grants ainda não são por módulo. Decisão **GATE A APROVADO**, detalhada com localização, teste e risco em `docs/reviews/SPRINT01_AUDIT.md`.

## 4. Sprint 02 — Implementação

| Funcionalidade | Situação | Arquivos | Testes | Observações |
|---|---|---|---|---|
| Perfis: criar, editar, listar, arquivar, reativar, nome/emoji e limite de cinco ativos | IMPLEMENTADO | `apps/finance/views.py`, `services/profiles.py`, `models.py`, `templates/finance/profile_*.html` | `test_finance_views.py`, `test_finance_services.py`, `test_sprint02_views.py`, `test_audit_permissions.py` | Lock no núcleo para criação/reativação; arquivados preservam histórico. |
| Isolamento, grants e seleção individual/combinada por mês | IMPLEMENTADO | `apps/core/permissions.py`, `apps/finance/query_forms.py`, `views.py` | `test_audit_permissions.py`, `test_sprint02_views.py` | Admin vê perfis do próprio núcleo; comum precisa grant; IDs externos rejeitados. |
| Contas bancárias/dinheiro físico e saldos desconhecidos | IMPLEMENTADO | `apps/finance/services/accounts.py`, `services/records.py`, `forms.py`, `views.py` | `test_finance_views.py`, `test_finance_services.py` | Consulta inclui arquivadas; cadastro não cria lançamentos. |
| Renda ausente, zero, positiva e exclusão da informação | IMPLEMENTADO | `apps/finance/query_forms.py`, `services/records.py`, `views.py` | `test_sprint02_views.py` | `NULL` distinto de zero; saldo não entra na renda. |
| Despesas previsíveis e imprevisíveis | IMPLEMENTADO | `apps/finance/forms.py`, `services/records.py`, `domain/planning.py`, `views.py` | `test_sprint02_views.py`, `test_finance_services.py` | Dia 1–31; mês curto usa último dia; data imprevisível é do servidor; sem débito implícito. |
| Posições de investimento, metas opcionais e Reserva | IMPLEMENTADO | `apps/finance/services/metrics.py`, `domain/calculations.py`, `domain/planning.py`, `forms.py`, `views.py` | `test_sprint02_views.py`, `test_finance_services.py`, `test_calculations.py` | Meta Reserva automática; aporte sugerido por perfil sem rendimento presumido. |
| Interface Claro/Escuro, sidebar, botões `+`, lápis, modal e responsividade | IMPLEMENTADO | `templates/finance/*`, `static/finance/alece.css`, `alece.js` | Testes HTTP de POST/erros e QA visual em quatro larguras | QA do navegador usou HTML sintético gerado pelo Django; falta jornada interativa autenticada com servidor. |
| Gestão visual de membros e grants por módulo | PENDENTE | — | — | Fora da entrega de cadastros; autorização por perfil funciona. |
| Pagamentos, estornos complexos e conciliação | PENDENTE | — | — | Deliberadamente fora do Sprint 02; cadastro não equivale a confirmação bancária. |

## 5. Alterações de código

Criados nesta intervenção: `AGENTS.md`; `apps/core/auth_forms.py`, `auth_services.py`, `migrations/0002_authenticationattempt.py`; `apps/finance/forms.py`, `query_forms.py`, `urls.py`, `views.py`, `domain/planning.py`, `services/accounts.py`, `services/metrics.py`, `services/records.py`, `migrations/0002_sprint02_catalogs.py`; `config/test_settings.py`; `static/finance/alece.css`, `alece.js`; templates em `templates/finance/`; testes em `tests/test_auth_security.py`, `test_audit_permissions.py`, `test_finance_services.py`, `test_finance_views.py`, `test_sprint02_views.py`; relatórios em `docs/reviews/`. Alterados: `apps/core/auth_views.py`, `models.py`, `permissions.py`, `views.py`; `apps/finance/admin.py`, `models.py`, `services/profiles.py`, `services/ledger.py`; `config/settings.py`, `config/urls.py`; `.github/workflows/ci.yml`, `release.yml`; `Dockerfile`, `pyproject.toml`, `CHANGELOG.md`, `README.md`, `RUNBOOK.md`, `docs/ARCHITECTURE.md`, `CI_CD.md`, `DOMAIN.md` e templates de autenticação. Removido `test_recovery.py`, script manual com credencial e impressão de sessão/código. O protótipo em `reference/prototype/` foi preservado.

Decisão arquitetural: a view autoriza por objeto, o serviço faz escrita atômica e revalida permissão, o domínio calcula com `Decimal`; nenhum signal/view altera saldo. Cadastros ligados ao ledger não são apagados. Nenhuma dependência de aplicação foi adicionada. O `Dockerfile` atualiza `pip` para a linha 26.2 corrigida antes de instalar as dependências por faixa. `config/test_settings.py` usa armazenamento estático simples durante testes, sem exigir `collectstatic` no bind; a imagem real faz `collectstatic`.

## 6. Banco de dados

`core.0002_authenticationattempt` acrescenta controle persistente de tentativas e versão de código de recuperação. `finance.0002_sprint02_catalogs` acrescenta `FinancialProfile.is_archived`, `InvestmentPosition.recorded_on`, `ck_recurring_due_day_range` e `ck_reserve_no_manual_target`. As constraints anteriores de renda/saldo não negativos, valores positivos, unicidades e FKs continuam. `BankAccount`, despesas e investimentos mantêm FK `PROTECT` ou bloqueio pelo serviço quando há ledger. `ProfileGrant.clean()` rejeita workspace divergente e os filtros de leitura ignoram grants cruzados. O limite de cinco usa lock transacional do `Workspace`; inserções SQL externas sem serviço não recebem essa garantia.

Os 90 testes rodaram com PostgreSQL 16, não SQLite. Em banco efêmero, `finance.0002` passou upgrade/downgrade/re-upgrade e preservou perfil legado. Uma posição legada Reserva com `target_amount` não nulo fez a migração falhar sem alterar a linha. Pré-migração em base real: backup PostgreSQL verificado, `SELECT COUNT(*) FROM finance_investmentposition WHERE category='reserve' AND target_amount IS NOT NULL;`, análise/correção supervisionada de linhas encontradas, ensaio numa cópia e janela de implantação. **Nenhuma** migração persistente foi feita. Rollback de schema após uso perde os novos estados de arquivamento/data; restaurar DB de backup é a rota segura quando houver dados gravados.

## 7. Regras financeiras

- Renda mensal é fluxo informado: `NULL`, `0,00` e positivo têm significados distintos. Alterá-la/limpá-la recalcula o resumo na leitura e não cria `TransactionBatch`.
- Saldo é posição de cada conta: `NULL` desconhecido não vira zero; o resumo soma apenas saldos conhecidos de contas não arquivadas e mostra a contagem de desconhecidos. Saldo e patrimônio nunca entram na renda mensal.
- Despesa previsível ativa entra no orçamento por categoria. Dia 31 em fevereiro de 2026 é exibido como 28/02/2026. Imprevisível tem data do servidor, consulta mensal e separação entre valor cadastrado ainda pendente e batches de pagamento confirmados existentes; nenhum cadastro confirma pagamento.
- Posições ativas somam `current_value` por categoria; `applied_amount` e `target_amount` permanecem separados. Metas das três categorias de objetivos são opcionais. Meta da Reserva = despesas essenciais mensais × cobertura (9 meses por padrão, 6–12 permitido). Exemplo realmente testado: essencial `R$ 10,01` × 9 = `R$ 90,09`; Reserva atual `R$ 1,00`, lacuna `R$ 89,09`.
- Disponível mensal = `max(0, renda - essenciais - estratégicas - discricionárias - imprevisíveis confirmadas no mês)`. Reserva sugerida = `min(disponível, lacuna da Reserva)`; o restante é dividido entre três objetivos com pesos 1:1:1 e distribuição exata de centavos. Reserva concluída tem sugestão zero e continua visível. Prazo estimado = teto da lacuna ÷ sugestão mensal somente se houver meta e sugestão positiva; nenhum rendimento futuro é presumido. No teste com renda `R$ 100,00`, despesas previsíveis `R$ 15,01` e confirmado `R$ 2,34`, disponível = `R$ 82,65`, todo sugerido à Reserva ainda incompleta.
- Perfis combinados somam apenas perfis ativos autorizados. Rendas e saldos têm totais separados com contagem de valores desconhecidos; não há mistura de dados de workspace alheio.

## 8. Segurança

Autenticação Django com login, logout, troca de senha e recuperação offline corrigida. Emissão de novo código exige sessão e senha atual; endpoint público antigo não emite código. Hash de código, versão de invalidação, resgate único com lock, quota persistente e validadores da senha foram testados. CSRF middleware protege POSTs e há teste de requisição sem token. O redirecionamento pós-login valida host e esquema.

Todas as consultas financeiras partem de membership e perfis autorizados; administradores acessam todos os perfis do próprio workspace; comuns dependem de grants, e `can_edit` implica leitura. Revogação vale na próxima requisição/chamada de serviço. Views rejeitam identificadores manipulados; mutações de serviço reverificam perfil e vínculo do objeto, inclusive sob concorrência. O Admin financeiro é somente leitura. Dados de QA são sintéticos; logs não contêm secrets nem dados financeiros privados. **Planejado, não implementado:** gestão visual de grants, RLS no PostgreSQL, rate limit por infraestrutura/proxy e política fina por módulo. A implantação deve configurar TLS, cookies e proxy conforme `RUNBOOK.md`.

## 9. Testes e evidências

| Verificação | Comando | Resultado | Evidência |
|---|---|---|---|
| Gate A | `pytest -q -p no:cacheprovider --tb=short` | 69/69, 0 falhas, 0 ignorados | `docs/reviews/SPRINT01_AUDIT.md`; log em HOME |
| Regressão final Sprint 02 | mesmo comando, runtime Docker isolado | **90 coletados, 90 aprovados, 0 falhas, 0 ignorados**, 8 subtestes; 47 avisos de `staticfiles` em bind | `docs/reviews/SPRINT02_REPORT.md`; log em HOME |
| Django | `python manage.py check` | 0 problemas | log em HOME |
| Migrações declarativas | `python manage.py makemigrations --check --dry-run` | Sem mudanças | log em HOME |
| Qualidade | `ruff check .`; `git diff --check` | Aprovados | log em HOME e checkout Git |
| Migração de dados/schema | script externo `migration_probe.py` executado em runtime com PostgreSQL efêmero | Upgrade/downgrade/re-upgrade aprovado; legado inválido rejeitado sem dano | stdout do ensaio; relatório Sprint 02 |
| Build/estáticos | `docker build -t alece:sprint02-local .` | Aprovado; 129 estáticos copiados e 387 pós-processados | saída do build local |
| Dependências | `python -m pip_audit -r /app/requirements/production.txt` na rede Docker bridge; checagem separada `pip==26.2.1` | Sem vulnerabilidades conhecidas nas versões resolvidas | saída do scanner; imagem confirmou `pip 26.2.1` |
| Navegador | Edge/CDP em HTML sintético gerado pelo Django | 320/390/768/1440 px, quatro telas, sem overflow da página; modal e alternância claro/escuro inspecionados | imagens em HOME/.codex/visualizations/.../alece-qa/ |
| GitHub Actions remoto / E2E autenticado em navegador | **NÃO EXECUTADO** | Sem credenciais/ação remota autorizada; QA visual usou fixtures sintéticas | risco operacional registrado |

A primeira rechecagem do scanner na rede Docker interna falhou por DNS isolado; não foi tratada como aprovação. A repetição com rede bridge e acesso ao índice passou. O scanner de pacotes instalados no runtime de auditoria encontrou `pip 25.0.1` com avisos, por isso a imagem de aplicação passou a instalar `pip 26.2.1`, cuja versão foi verificada e auditada separadamente. Resultados da CI remota não foram inventados.

## 10. CI/CD e infraestrutura

`.github/workflows/ci.yml` usa PostgreSQL de serviço para checks, migração, testes e auditoria de dependências, além de build Docker. `.github/workflows/release.yml` deixou de publicar em qualquer push de tag: requer `workflow_dispatch`, referência de tag `v...` e `publish=true`; permissão `packages:write` ficou no job de publicação. Não existe deploy automático ao ZimaOS. O pipeline remoto não foi acionado aqui. Localmente, o banco de auditoria foi PostgreSQL 16 em `tmpfs` e rede interna sem portas publicadas; os serviços persistentes preexistentes ficaram intocados. O build `alece:sprint02-local` foi local, sem push. Os requirements permanecem por faixas, sem lockfile hashado; CI e rebuild futuro podem resolver versões diferentes. Healthchecks de liveness não substituem um ensaio de readiness/migração em staging.

## 11. Backups e rollback

Backup inicial do código: `C:/Users/Caio Tomaz/backups/2026-10-18_07-58-15__alece-source.zip`, SHA-256 `882505a179711225c3a2db4526f1ca88dcef09aa190fae4a23ac142d0f2efde5`. Checkpoint posterior do código: `C:/Users/Caio Tomaz/backups/2026-10-18_13-26-54__alece-sprint02-checkpoint.zip`, SHA-256 `0c6a6e19d4b9cec39d0cee529ea0f883e9616bcd515354b261797a747b290557`. Ambos tiveram SHA-256 e integridade ZIP verificados. Log principal: `C:/Users/Caio Tomaz/logs/2026-10-18_07-58-15.log`; contém comandos/resultados, sem secrets ou finanças privadas. Os ZIPs **não** são backup de PostgreSQL.

Para recuperar código, preservar o checkout atual, extrair backup em diretório separado, comparar e reverter commits locais específicos se necessário. Para migração real futura, gerar `pg_dump` em HOME/backups, verificar SHA-256 e restauração numa cópia antes da mudança. Reverter `finance.0002` após gravar arquivamento/data perde esses campos; restaurar backup de DB ou construir migração compensatória é necessário. Reverter `core.0002`/código de autenticação antigo pode reabrir vulnerabilidades e permitir códigos legados; não fazer rollback inseguro para operar.

## 12. Problemas e riscos

| Gravidade | Problema remanescente | Impacto / ação |
|---|---|---|
| Alta para implantação | Posições legadas Reserva com `target_amount` bloqueiam `finance.0002` | Executar preflight em cópia, decidir correção caso existam registros e fazer backup verificado. Não impede revisão local. |
| Média | Sem lock de dependências com hashes e sem execução de GitHub Actions remoto | Rebuild pode mudar versões; validar CI e resolução antes de release. |
| Média | Autorização por perfil, não por módulo; não há tela de gestão de membros/grants | Administração operacional ainda depende do Admin/rotina confiável; revisar política para Sprint 03. |
| Média | Pagamentos/estornos complexos e reconciliação fora do Sprint 02 | Resumo de pagamentos existentes não deve ser tratado como extrato completo em estornos entre meses. |
| Média | E2E de navegador autenticado não executado | Testes HTTP cobrem fluxo e CSRF, mas falta jornada visual contra servidor real antes de produção. |
| Baixa | 47 avisos de pasta `staticfiles` ausente no bind de testes | Build de produção coletou estáticos; opcional ajustar middleware do teste. |

## 13. Próximas etapas

Proposta de **Sprint 03**, não iniciada: (1) preparar staging com cópia anonimizada do banco, backup/restore verificado, preflight de meta legada e ensaio de migração/rollback; critério: zero linhas inválidas ou decisão documentada, migração reversível conforme plano e CI remota verde. (2) criar interface segura de membros/grants, decidir granularidade por módulo em ADR e testar revogação, IDOR e administradores de núcleos distintos. (3) especificar pagamento confirmado/estorno e conciliação com ledger antes de habilitar botões de movimentação; critérios: idempotência, centavos, concorrência e correção entre meses em PostgreSQL. (4) adicionar jornada E2E autenticada nos tamanhos 320/390/768/1440, tema Claro/Escuro e acessibilidade de modais. Depois disso, avaliar lock hashado e importação CSV/PDF com casos malformados e duplicados; não inferir esses fluxos como já implementados.

## 14. Decisão técnica final

**SPRINT 02 APROVADO PARA REVISÃO.** O fluxo de cadastros e consultas solicitado funciona e passou a regressão de 90 testes em PostgreSQL isolado, checks, migração ensaiada, lint, scanner de requisitos e build local. A revisão deve decidir o tratamento de dados legados e dos riscos da seção 12 antes de qualquer plano de produção. Aprovação para revisão não equivale a release estável nem aprovação para deploy.

## 15. Mensagem de continuidade para o ChatGPT

### MENSAGEM PARA ENVIAR AO CHATGPT

Revise tecnicamente o projeto ALECE no checkout `codex/sprint01-audit-sprint02` (commit de consolidação `a1832e69626d3c987217ed74ee6c19104d2290b`; execute `git rev-parse HEAD` para o commit final com este panorama e a correção visual). A base auditada foi `e9e36a6e05a86626f3ac2ee77e9178fcc7676ecb`. O Gate A do Sprint 01 foi aprovado após corrigir tomada de conta na recuperação offline, replay/força bruta, validadores de senha, open redirect, grants cruzados e bypass de escrita financeira pelo Admin: 69/69 testes PostgreSQL passaram. No Sprint 02 foram entregues perfis ativos/arquivados com limite transacional de cinco, contas e dinheiro físico com saldo `NULL` distinto de zero, renda editável/limpável, despesas previsíveis/imprevisíveis, posições e metas de investimento, Reserva calculada, seleção autorizada de perfis/mês e interface Claro/Escuro baseada no protótipo. Cadastros não geram movimentações bancárias. A regressão final teve 90/90 testes PostgreSQL, 0 falhas, 0 ignorados e 8 subtestes; Django check, sem drift de migração, Ruff, build Docker local e auditoria de requirements passaram. A migração `finance.0002` foi ensaiada com upgrade/downgrade/re-upgrade em PostgreSQL efêmero; legado Reserva com meta manual é rejeitado sem dano e exige preflight/correção antes de base real. O browser QA inspecionou HTML sintético em 320/390/768/1440 px e tema claro, mas não uma jornada E2E autenticada. Nenhum banco persistente, credencial real, push, publicação ou deploy foi tocado. Leia `docs/reviews/SPRINT01_AUDIT.md`, `SPRINT02_REPORT.md`, este panorama, `docs/SPEC_ORIGINAL_COMPLETA.md` e `docs/DOMAIN.md`. Riscos: legado que bloqueia migração, requirements sem lock, CI remota não executada, grants somente por perfil e conciliação/estornos fora do escopo. Perguntas para a revisão: a política para metas legadas da Reserva deve ser limpar, migrar ou bloquear caso a caso? Qual granularidade de grants por módulo é exigida? Que critérios de aceite e testes PostgreSQL definem pagamento confirmado e estornos entre meses? O Sprint 02 está aprovado para revisão, não para produção; proponha o Sprint 03 sem presumir funcionalidades não validadas.
