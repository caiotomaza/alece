# ALECE — instruções permanentes

- Monólito Django 5.2 / PostgreSQL: views autorizam, serviços transacionais persistem, domínio calcula com Decimal e arredondamento explícito. Não escrever saldos em views/signals.
- Consulte `docs/SPEC_ORIGINAL_COMPLETA.md`, `docs/DOMAIN.md` e ADRs antes de alterar regras financeiras. Cadastro de renda/despesa/posição não confirma movimentação bancária.
- Administrador acessa todos os perfis do próprio workspace; Comum precisa de grant; edição implica leitura. Nunca aceitar workspace/perfil enviado pelo cliente sem autorização por objeto. Revogações valem na próxima requisição.
- Até cinco perfis **ativos** por workspace, com bloqueio transacional na criação/reativação. Arquivados preservam histórico.
- Dinheiro desconhecido (`NULL`) é distinto de zero. Não somar saldo/patrimônio à renda. Não apagar objetos ligados ao ledger.
- Preserve o protótipo em `reference/prototype/`; componentes ativos usam tokens Claro/Escuro, sidebar, `+` por seção, lápis por linha e modais com ações no rodapé.
- Verificações: `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `ruff check .`, `pytest -q`. Exigem dependências instaladas e variáveis ALECE em banco efêmero; concorrência exige PostgreSQL, não SQLite. Não apontar testes para dados reais.
- Antes de alterar estado existente, registre log em HOME/logs e backup necessário em HOME/backups com SHA-256 verificado. Preserve mudanças preexistentes, logs e backups.
- Não publicar, fazer push, implantar, alterar credenciais reais ou migrar banco persistente sem autorização específica. Nunca registrar secrets ou conteúdo financeiro privado.
