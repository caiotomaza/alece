# Auditoria geral do ALECE — 23/10/2026

## Escopo e estado

Auditoria local da branch `codex/sprint01-audit-sprint02`, iniciada em `ab55453`. O estado inicial continha 16 arquivos rastreados modificados e arquivos não rastreados. Nenhum banco persistente, container das portas 8000/8001/8002, credencial real ou volume de produção foi alterado. A homologação usa o projeto Compose `alece-audit`, PostgreSQL 16 sintético em `127.0.0.1:55433` e aplicação em **http://127.0.0.1:8003/**.

Antes da primeira edição, foi criado `C:\Users\Caio Tomaz\logs\2026-10-23_09-04-45.log` e backup de código/documentação em `C:\Users\Caio Tomaz\backups\2026-10-23_09-04-45__alece_pre_audit.zip`. SHA-256 gerado e verificado: `BFA6BCC0A1F79F3195922171D26E387809304DE5D1FDE502798516692017E19B`. O backup não contém `.env`, cookies nem dados financeiros. A restauração de código exige conferência do hash e revisão do diff; migrações de banco só devem ser revertidas a partir de dump validado do ambiente correspondente.

## Matriz de evidências

| Área | Evidência examinada | Resultado |
| --- | --- | --- |
| Autenticação e primeiro cadastro | `apps/core/bootstrap.py`, middleware, views, testes de disputa e bind | Lock advisory dentro da transação, segunda verificação após lock, login manual; setup só com publicação em loopback. |
| Usuários, grants e perfis | Views, `apps/core/permissions.py`, serviços, testes de revogação/concorrência | Admin do próprio núcleo; Comum com grant por objeto; limite de cinco perfis ativos. |
| Contas, despesas e competências | Modelos, serviços, testes e cadastro E2E sintético | Cadastro de despesa não cria lançamento bancário; `NULL` permanece desconhecido. Registro e log compartilham transação. |
| Ledger e investimentos | Serviços, triggers/migrações, testes de partidas dobradas/estorno e `preflight_finance --strict` | Histórico postado protegido; movimentações dependem de serviço transacional. |
| Importação e conciliação | Parsers CSV/OFX, stage/commit, testes de isolamento e idempotência | Correções de cabeçalho, rejeição de XML perigoso, travamento e escopo por perfil. |
| Relatórios | `apps/finance/services/reports.py` e testes | Corrigida inicialização de total patrimonial e serialização de datas. |
| Logs | Serviço, views, trigger PostgreSQL e testes | Leitura integral restrita a Admin do núcleo/superusuário operacional, sanitização de novos eventos e bloqueio de UPDATE/DELETE. |

Validação local mais recente: **300 testes e 8 subtestes aprovados** em PostgreSQL isolado; `manage.py check` sem problemas; `makemigrations --check --dry-run` sem mudanças; Ruff e `compileall` aprovados; `preflight_finance --strict` sem problemas; build Docker concluído e containers `alece-audit-db-1` e `alece-audit-web-1` saudáveis. `pip-audit --no-deps --disable-pip` não encontrou vulnerabilidades conhecidas nos pins diretos dos locks de produção e desenvolvimento. A auditoria transitiva completa no Windows falhou na resolução da dependência condicional não pinada `tzdata`; isso não é um resultado de ausência de vulnerabilidades transitivas. O build Linux instalou o lock de produção com hashes. CI remota não foi executada, pois não houve push. Os relatórios históricos em `docs/reviews/` descrevem etapas anteriores e não constituem prova desta auditoria.

## Alterações e limites

Foram corrigidos defeitos reproduzidos em autorização, bootstrap, importação, relatórios, backup com saldo desconhecido e logs. A navegação ativa tem cinco destinos. Nesta segunda intervenção, o shell, os cards, gráficos, formulários e modais foram comparados com o protótipo em 80 cenários de página e 48 de modal. **A equivalência visual ao protótipo v1.32.1 permanece pendente**, conforme `ALECE_VALIDACAO_VISUAL_V1.32.1.md`. Logs criados por versões anteriores não foram reescritos, para preservar histórico; sua eventual exposição de metadados deve ser avaliada antes de migrar um banco persistente. Não classificar a versão como conclusão visual nem como homologação de produção. O ambiente sintético pode ser descartado sem afetar instalações existentes; nunca usar `down -v` em outro projeto Compose.

## Validação e rollback

Executar `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python -m ruff check .`, `python -m pytest -q`, `preflight_finance --strict`, auditoria dos locks e `docker compose -f compose-audit.yaml build web` no ambiente isolado antes de qualquer merge. Registrar contagem e resultado final reais ao encerrar a rodada. Para rollback local, preservar os arquivos preexistentes e rever commits individuais; para banco persistente, planejar backup e restauração próprios antes de migração autorizada.

## Continuação visual iniciada em `cf4ae6f`

O estado rastreado inicial estava limpo; cinco arquivos não rastreados preexistentes foram preservados. Antes de editar, foram criados `C:\Users\Caio Tomaz\logs\2026-10-23_13-51-30.log` e `C:\Users\Caio Tomaz\backups\2026-10-23_13-51-30__alece_frontend_prework.zip`, com SHA-256 gerado e conferido: `4bdf86b00b9083bf4fe694ee4902d6f4e3552b3b0523d1c03192e7d8119a6381`. As capturas finais organizadas em `C:\Users\Caio Tomaz\backups\alece_visual_evidence_2026-10-23\final` não entram no Git por conterem números do protótipo.

O read model passou a gerar distribuição mensal e séries apenas a partir de dados autorizados e lotes confirmados, preservando `NULL` e `Decimal`. As listas de importação e relatórios tiveram vazamento entre perfis corrigido; a exportação CSV de investimentos e metas passou a produzir CSV real. Novos testes cobrem isolamento, revogação, conteúdo de exportação e origem autorizada do upload. O formulário de importação na página de Movimentações continua apenas estágio; confirmação exige a operação própria de conciliação. O E2E validou persistência e separação do ledger, seleção de perfil/mês, tema, modais, permissões e logs. Não houve migrations novas, push, deploy ou acesso a banco persistente.
