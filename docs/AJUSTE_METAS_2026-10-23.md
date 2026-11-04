# ALECE — Ajuste de título e metadados de Metas (2026-10-23)

## Escopo

- O título **Metas** permanece dentro do cartão na tela `/investimentos/`, com margem superior interna zerada. O espaço entre a borda e o título passa a ser determinado somente pelo padding do cartão, tanto no desktop quanto em celulares.
- Removido o indicador redundante **Perfil financeiro / Principal**. O seletor de perfis da navegação continua funcionando; nenhum perfil foi removido do banco.
- Preservados os cálculos, cartões financeiros, permissões, URLs, migrações, formulários e serviços.

## Verificação

- Teste estático do template e validação sintática dos dois CSS.
- Chromium, prévia estática usando CSS real: 320, 390, 768 e 1280 px, temas claro e escuro; margem superior computada em `0px`; sem overflow horizontal.
- A prévia é independente do backend: **não** comprova renderização Django nem operações no PostgreSQL.

## Atualização segura

1. Na instalação atual, antes de substituir os arquivos, faça backup verificável do diretório do projeto (inclusive `.env`) e dump do PostgreSQL, com SHA-256 dos dois backups. Preserve os volumes do Docker.
2. Extraia este ZIP completo em um novo diretório, sem remover os volumes anteriores. Caso tenha configurações próprias, preserve-as sem sobrepor segredos do ambiente existente.
3. Execute `docker compose config` para validar o Compose, depois `docker compose up -d --build web` e verifique o healthcheck e as telas `/investimentos/`, `/visao-geral/` e `/configuracoes/`.
4. Os logs da execução do container web ficam em `src/logs/`, se `ALECE_LOG_VALIDACAO=true`.
5. Se ocorrer falha, restaure a versão anterior do projeto e sua configuração, reconstrua o serviço web e valide novamente. Restaurar PostgreSQL exige avaliação específica; não importe um dump antigo sobre um banco mais recente sem planejamento.

**Não use** `docker compose down -v`. Não foram adicionadas migrações nesta entrega.
