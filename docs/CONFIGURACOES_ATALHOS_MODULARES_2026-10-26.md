# ALECE — Configurações com atalhos administrativos

## Comportamento

- `/configuracoes/`: três ações pessoais para qualquer usuário autenticado e, apenas para administradores do espaço ativo, os seis cartões de administração.
- `/configuracoes/usuarios/`, `/configuracoes/perfis/`, `/configuracoes/apis/`: áreas de gestão independentes, com acesso restrito no backend e janelas modais quando JavaScript estiver disponível.
- `/logs/` e `/relatorios/`: páginas próprias, preservadas.
- **Redefinir ambiente**: item visível como indisponível, sem endpoint ou operação destrutiva não especificada.
- Nenhum dado é alterado ao abrir os cartões. Alterações existentes exigem formulários e verificações de permissão do Django.
- Nos temas claro/escuro e em telas móveis, cartões utilizam os mesmos tokens CSS do ALECE.

## Segurança

`settings_admin_panel` verifica pertinência ao espaço e papel de administrador via `require_workspace_admin` a cada requisição; controles de front-end não definem permissões.

## Implantação e reversão

Faça backup do PostgreSQL, dos volumes e do `.env` e valide seus SHA-256 antes de atualizar. Extraia o ZIP completo **dentro da pasta alece**, preservando as configurações locais. Recrie somente o serviço web com Docker Compose e valide `/configuracoes/`, `/configuracoes/usuarios/`, `/configuracoes/perfis/`, `/configuracoes/apis/`, `/logs/`, `/relatorios/`, nos papéis comum e admin.

Para reverter o ajuste de código, restaure a versão anterior do projeto, mantendo o banco/volumes existentes (não há migrations nesta alteração), valide os arquivos e reconstrua o serviço web. Backup dos arquivos modificados desta edição foi salvo em HOME/backups/ com SHA-256.

## Limites da validação

Compilação e testes estáticos não substituem testes de renderização Django/PostgreSQL e de navegador no Docker real.
