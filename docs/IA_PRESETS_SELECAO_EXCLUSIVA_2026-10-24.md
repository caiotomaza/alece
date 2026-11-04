# Integração de IA — presets e seleção exclusiva

- Provedores cadastrados permanecem disponíveis; **somente uma integração ativa por núcleo**.
- Ao alternar a chave na tabela, todas as outras chaves daquele núcleo são desligadas na mesma transação.
- A exclusividade é reforçada pelo índice único parcial `uq_alece_ai_one_active_ws` no PostgreSQL.
- Presets predefinidos têm `name`, `endpoint` e `model` controlados pelo catálogo do servidor; formulário exibe o resumo em modo leitura e pede a chave.
- Selecionar **Personalizada** exibe os campos editáveis. Hosts personalizados precisam constar em `ALECE_AI_ALLOWED_HOSTS` para transmissão.
- `ALECE_LOG_VALIDACAO=true` segue ativado em `.env` e `.env.example`; logs em `src/logs/`.
- Nunca são registrados tokens/chaves no PostgreSQL ou em auditorias; usam volume `app_ai_tokens`.
- O consentimento explícito antes de transmitir dados financeiros permanece obrigatório.

## Migração
`core.0009_one_active_ai_provider` preserva os cadastros e, havendo vários ativos em um mesmo núcleo, mantém ativa a integração **mais recentemente modificada**, desativando as demais antes de aplicar a restrição.

## Backup e rollback
Antes de atualizar, faça dump PostgreSQL e backup dos volumes e `.env` com SHA-256 validado. Não use `docker compose down -v`.
Em caso de falha, restaure **em conjunto** o dump pré-migração e a versão anterior do projeto. A migração é aditiva, mas o rollback do banco deve utilizar o backup (não desativar a constraint em produção sem planejamento).

## Validação necessária na instalação
`docker compose run --rm web python manage.py migrate --noinput`, `docker compose run --rm web python manage.py check` e testes Django/PostgreSQL. Confirmar a alternância dos switches e que qualquer segunda integração ativa seja recusada pelo banco.
