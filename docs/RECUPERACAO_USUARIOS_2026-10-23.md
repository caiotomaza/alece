# ALECE — Conta, recuperação offline e administração de usuários

Versão: 2026-10-23 — atualização do fluxo de autenticação e do painel de Configurações.

## Fluxo de recuperação obrigatório

- O primeiro administrador é autenticado após `/setup/` e enviado a `/configuracoes/codigos/` antes de poder utilizar o sistema.
- Usuários criados em **Configurações → Usuários → +** definem seus próprios códigos no primeiro acesso autenticado. O administrador **não tem acesso** aos códigos de outro usuário.
- Usuários de versões anteriores também passam pela configuração obrigatória após a migração; o código legado é revogado no momento em que o novo conjunto é criado.
- O backend gera seis códigos exclusivos de oito caracteres cada, usando `secrets` e alfabeto de 32 símbolos (40 bits/código). Requisições de recuperação são limitadas por conta/IP. Os códigos são persistidos apenas como HMAC-SHA256, vinculado à chave secreta do Django e ao ID do usuário.
- Emissão: os seis códigos são mostrados **somente na resposta de emissão**, com botões **Copiar** e **Baixar .txt**. O botão de concluir permanece desabilitado até que as duas ações sejam acionadas. O POST também exige marcações de cópia, download, nonce de sessão e seis códigos no banco. **O navegador não consegue provar que o arquivo foi guardado fora dele**: as duas ações representam confirmação operacional do usuário, não atestado de armazenamento.
- Se o usuário recarregar ou fechar a página antes de concluir, os códigos não são reexibidos. Ele pode criar um novo conjunto informando a senha atual; o anterior será revogado.
- Os códigos são independentes: quando um é usado em `/recovery/use/`, apenas aquele código é marcado como utilizado. Os outros continuam válidos. Após usar o último código, o acesso autenticado exige reconfigurar a recuperação.
- Alteração de senha própria ocorre em modal com senha atual, nova senha e confirmação. Django `PasswordChangeForm` e `update_session_auth_hash` mantêm segurança da sessão atual.
- Redefinição de códigos exige senha atual, invalida todos os seis anteriores e reabre a confirmação de cópia e download.
- As páginas de emissão têm `Cache-Control: no-store`. Logs não contêm o texto dos códigos, e nenhuma integração de IA recebe esses dados.

## Seção de usuários

Cada linha da tabela tem somente um lápis de gerenciamento. O botão + da seção é o único caminho para cadastrar usuário.

O modal do administrador contém:

1. Informações, papel e status da conta;
2. Permissões por perfil financeiro e módulo;
3. Quantidade de códigos de recuperação disponíveis (nunca o texto dos códigos);
4. Redefinição administrativa de senha;
5. Remoção de acesso ao núcleo (soft removal: preserva usuário sem acesso, logs e registros financeiros). O último administrador ativo é protegido.

Todas essas operações validam a função de administrador **no backend**, independentemente do HTML ou JavaScript.

## Mudanças de dados

Migration: `core.0008_recovery_code_set`, adiciona `RecoveryCode` e `UserProfile.recovery_acknowledged_at`. Não remove colunas antigas, facilitando rollback de código.

O ALECE **não envia códigos por e-mail** e não sincroniza cópias dos códigos entre dispositivos, por design. O arquivo .txt deve permanecer em local privado (idealmente gerenciador de senhas). Não envie esse arquivo ao suporte nem a APIs.

## Implantação e rollback

1. Antes de copiar arquivos novos, faça backup do escopo modificado e **dump PostgreSQL** no HOME do operador. Valide SHA-256 imediatamente.
2. Aplique o patch somente na raiz de projeto compatível; preserve `.env`, `app_pgdata`, `app_media`, `app_secrets`, logs e demais volumes.
3. `docker compose config -q` antes da mudança; `docker compose up -d --build web` após.
4. Confira `python manage.py check`, a migration `core.0008`, os endpoints `/health/ready/` e o fluxo real no navegador para primeiro acesso, troca de senha, download, uso de um código e edição de usuários.
5. Rollback de **código**: restaurar arquivos do ZIP de backup após parar o serviço web. Rollback de **banco**: restaurar o dump feito antes da migração em ambiente isolado, verificando que não haverá perda de alterações posteriores. Não faça `docker compose down -v` nem remova backups automaticamente.

O arquivo ZIP incremental inclui `Aplicar-ALECE-Recuperacao.ps1`, que realiza o dump e backup antes de copiar o patch, além do log e validações. A aplicação **não pode ser declarada verificada em Docker** até esses testes serem executados na máquina de destino.

## Limitações verificáveis

- Instalação e regressão Django/PostgreSQL não foram executadas neste ambiente, que não dispõe do Django 5.2.18 nem de Docker. Os testes de integração estão em `tests/test_recovery_six_codes.py`, para execução no CI que disponibiliza PostgreSQL 16.
- Os códigos devem ser tratados como credenciais de emergência; oito caracteres em base32 são cerca de 40 bits de entropia. O limitador de tentativas online deve permanecer ativo e devem ser monitoradas tentativas suspeitas.
- Criação de usuário não transfere a lista de códigos ao administrador; a lista é gerada e exibida somente ao próprio titular após login. Isso evita acesso indevido de administradores a credenciais futuras de recuperação.
