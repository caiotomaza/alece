# Progresso da intervenção — 2026-10-18

- Base: e9e36a6e05a86626f3ac2ee77e9178fcc7676ecb; alterações anteriores preservadas.
- Branch: codex/sprint01-audit-sprint02.
- Backup de código: C:/Users/Caio Tomaz/backups/2026-10-18_07-58-15__alece-source.zip.
- SHA-256 validado: 882505a179711225c3a2db4526f1ca88dcef09aa190fae4a23ac142d0f2efde5.
- Log: C:/Users/Caio Tomaz/logs/2026-10-18_07-58-15.log.
- Ambiente isolado: rede Docker interna alece-audit-20261018, PostgreSQL 16 em tmpfs, sem portas publicadas. Nenhum acesso aos containers alece-web-1/alece-db-1 existentes.

## Sequência e decisões

1. Inspeção e backup concluídos. Auditoria e correções de segurança em andamento.
2. Gate A ainda não decidido. Não iniciar Sprint 02 antes dos testes PostgreSQL essenciais.
3. Após aprovação: cadastros financeiros, consolidação e interface conforme protótipo; depois regressão, migrações/build e relatórios.
4. Política documental aplicável: SPEC_ORIGINAL_COMPLETA RF-055, RF-058 e seção de permissões: administrador acessa todos os perfis de seu núcleo; edit implica view; máximo cinco perfis ATIVOS. Corrige divergência da implementação anterior. Usuários comuns dependem de grants.
5. Cadastro não confirma pagamentos. Histórico ligado a ledger nunca será apagado por CRUD.
6. Nenhuma publicação, push, release ou deploy autorizado.

## Fontes oficiais consultadas

- https://docs.djangoproject.com/en/5.2/releases/5.2/ — compatibilidade Python (3.14 a partir de 5.2.8).
- https://docs.djangoproject.com/en/5.2/ref/models/querysets/ — select_for_update e diferenças de testes SQLite/PostgreSQL.
- https://docs.djangoproject.com/en/5.2/topics/testing/tools/ — TransactionTestCase para concorrência.
