# Progresso da intervenção — 2026-10-18

- Base: e9e36a6e05a86626f3ac2ee77e9178fcc7676ecb; alterações anteriores preservadas.
- Branch: codex/sprint01-audit-sprint02.
- Backup de código: C:/Users/Caio Tomaz/backups/2026-10-18_07-58-15__alece-source.zip.
- SHA-256 validado: 882505a179711225c3a2db4526f1ca88dcef09aa190fae4a23ac142d0f2efde5.
- Log: C:/Users/Caio Tomaz/logs/2026-10-18_07-58-15.log.
- Ambiente isolado: rede Docker interna alece-audit-20261018, PostgreSQL 16 em tmpfs, sem portas publicadas. Nenhum acesso aos containers alece-web-1/alece-db-1 existentes.

## Sequência e decisões

1. Inspeção, backup, auditoria e correções de segurança concluídos. Veja SPRINT01_AUDIT.md.
2. Gate A aprovado com 69/69 testes PostgreSQL. Sprint 02 aprovado para revisão, sem autorização de produção.
3. Cadastros e interface do Sprint 02 integrados; migration finance.0002 validada com upgrade/downgrade/re-upgrade e rejeição segura de legado inválido. Regressão final: 90/90 testes PostgreSQL, check, sem drift, ruff e build local aprovados. Ver `SPRINT02_REPORT.md`.
4. Política documental aplicável: SPEC_ORIGINAL_COMPLETA RF-055, RF-058 e seção de permissões: administrador acessa todos os perfis de seu núcleo; edit implica view; máximo cinco perfis ATIVOS. Corrige divergência da implementação anterior. Usuários comuns dependem de grants.
5. Cadastro não confirma pagamentos. Histórico ligado a ledger nunca será apagado por CRUD.
6. Nenhuma publicação, push, release ou deploy autorizado.

## Fontes oficiais consultadas

- https://docs.djangoproject.com/en/5.2/releases/5.2/ — compatibilidade Python (3.14 a partir de 5.2.8).
- https://docs.djangoproject.com/en/5.2/ref/models/querysets/ — select_for_update e diferenças de testes SQLite/PostgreSQL.
- https://docs.djangoproject.com/en/5.2/topics/testing/tools/ — TransactionTestCase para concorrência.

- Checkpoint posterior Sprint 02: `C:/Users/Caio Tomaz/backups/2026-10-18_13-26-54__alece-sprint02-checkpoint.zip`, SHA-256 `0c6a6e19d4b9cec39d0cee529ea0f883e9616bcd515354b261797a747b290557`, verificado.
- Checkpoint início Sprint 03: `C:/Users/Caio Tomaz/backups/2026-10-18_14-14-44__alece-sprint03-source.zip`, SHA-256 `B349558C58076C3A651646AFCB52335F5192CB745A506EE6687D805543EC7CCF`.
- Checkpoint retomada Sprint 03: `C:/Users/Caio Tomaz/backups/2026-10-18_14-55-57__alece-sprint03-resume.zip`, SHA-256 `DE549D1378053EFFE1A33934C042981F2DC42F6ED27B416B16E01749E82DEC53`.
- Resolução dos dois apontamentos do teste em navegador:
  1. Distinção de saldo totalmente desconhecido (`NULL`) de saldo conhecido igual a zero (`0.00`) no modelo de leitura `profile_summary`, no template da Visão Geral e nos resumos por perfil.
  2. Integração do estorno de movimentações ao modal de edição previsto no protótipo v1.32.1 (`Editar movimentação`), com substituição do botão inline na tabela pelo lápis de linha e confirmação nativa.
- Auditoria contábil e de concorrência: 109/109 testes aprovados no PostgreSQL 16 efêmero, abrangendo partidas dobradas, bloqueios pessimistas `select_for_update`, integridade contra saldo negativo e imutabilidade auditável via triggers PL/pgSQL.
- E2E autenticado executado com servidor real e dados sintéticos em 320, 390, 768 e 1440 pixels, nos temas Claro e Escuro, gerando 48 capturas de tela integrais em `docs/reviews/screenshots/`.
- Verificações finais: Ruff 100% limpo, Compileall 100% limpo, Django check 0 erros, makemigrations drift 0 alterações, preflight_finance strict aprovado, pip-audit (produção e dev) sem vulnerabilidades e build Docker com hash-pinning verificado.
- Nenhuma publicação, push, release ou deploy executado. Base pronta para revisão independente e preparação do Sprint 04.
