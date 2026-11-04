# Configurações — gestão em páginas completas (27/10/2026)

## Correção

Os atalhos **Gerenciar usuários**, **Gerenciar perfis financeiros** e **Gerenciar APIs de IA** em `/configuracoes/` navegam para **páginas completas**, com o mesmo cabeçalho, largura de conteúdo e tabelas responsivas das demais áreas do ALECE. O JavaScript não intercepta mais esses três atalhos como modal.

| Área | Rota pública | Permissão |
|---|---|---|
| Usuários | `/configuracoes/usuarios/` | Administrador do espaço |
| Perfis | `/configuracoes/perfis/` | Administrador do espaço |
| APIs de IA | `/configuracoes/apis/` | Administrador do espaço |

Os **botões `+` e lápis** continuam a abrir os formulários existentes como pop-ups. Sem JavaScript, são links normais para formulários navegáveis. Depois de cadastrar ou alterar os registros, o retorno leva à respectiva página de gestão. Em Configurações, os três atalhos pessoais continuam disponíveis a todos os usuários, e as páginas completas de Logs/Relatórios permanecem inalteradas.

## Segurança

Nenhuma rota nova de alteração de dados foi criada. As views de gestão continuam autorizadas no servidor por `require_workspace_admin`, independentemente de classes CSS, e todos os POST existentes continuam sujeitos a CSRF e validação. O botão **Redefinir ambiente** permanece indisponível.

## Implantação

1. Salve backup validado de projeto, `.env`, PostgreSQL e volumes Docker.
2. Extraia o ZIP completo dentro da pasta do ALECE, sem criar subpasta adicional, preservando segredos locais.
3. Execute `docker compose up -d --build --force-recreate --no-deps web`.
4. Teste os três atalhos com o console do navegador aberto, em modo claro/escuro e dispositivos móveis.
5. Verifique que cada tela tem URL própria, botão de retorno, tabela independente e nenhuma janela sobreposta; cadastre/edite um registro de teste e confirme retorno à lista.
6. Acesse diretamente cada uma das três rotas com usuário comum para verificar a recusa de acesso.

## Reversão

Restaurar o backup verificado do código, mantendo os dados/volumes; recriar apenas o serviço web e validar. Nenhuma migration foi criada ou alterada.

## Limite de verificação

A compilação e os testes estruturais não substituem teste Django/PostgreSQL nem validação visual de navegador integrada à execução real.
