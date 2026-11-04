# Edição da própria conta — Configurações

## Alteração
- Em **Configurações > Usuários**, o usuário autenticado continua listado com papel e status, mas sua própria linha **não oferece botão de edição**. Um traço neutro aparece na coluna Ações.
- As demais contas continuam com o ícone de lápis que abre o gerenciamento administrativo.
- Os próprios dados são editados somente pela ação **Minha conta > Editar suas informações**.
- Não houve alteração em autenticação, permissões, banco de dados, migrações ou operações financeiras.

## Implantação
O ZIP é o projeto completo, incluindo `.env` e `.env.example` com `ALECE_LOG_VALIDACAO=true`. Antes de aplicar sobre uma instalação existente, faça backup do banco PostgreSQL, dos volumes e das configurações atuais, com SHA-256 verificado. Não execute `docker compose down -v`. Reconstrua o serviço `web` depois de conferir as configurações.

## Validação
Faça login como administrador e abra `/configuracoes/`. Em Usuários, a linha da sua conta deve mostrar um traço, sem lápis; as outras linhas devem continuar com lápis. Confirme a opção **Minha conta > Editar suas informações**. Faça também um teste com outro administrador, porque o critério é o usuário autenticado, não um nome fixo.

## Rollback
Restaure o arquivo `src/view/templates/core/settings_dashboard.html` a partir do backup SHA-256 validado em `HOME/backups/` criado durante esta intervenção, ou restaure o projeto completo anterior. Acompanhe os logs em `HOME/logs/` e em `src/logs/` durante a implantação.
