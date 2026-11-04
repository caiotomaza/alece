# ALECE — entrega integral com logs ativos e recuperação corrigida

## Conteúdo

Este arquivo ZIP inclui o **projeto inteiro**, com `compose.yaml`, `docker/`, `src/`, `tests/`, `docs/`, `public/`, `.env` e `.env.example`. Não é um patch.

- `.env` e `.env.example`: `ALECE_LOG_VALIDACAO=true` e `ALECE_DEBUG=false`.
- `src/logs/.gitkeep`: preserva a pasta no arquivo; o serviço web escreve cada execução em `src/logs/YYYY-MM-DD_HH-MM-SS.log` (UTC), em paralelo ao console Docker.
- Corrige erro HTTP 500 após confirmação dos seis códigos: a relação `RecoveryCode.user` aponta para o **usuário Django**, não para `UserProfile`. Foram corrigidos `RecoveryEnrollmentMiddleware` e `UserProfile.has_recovery_code()`.
- O projeto mantém as funcionalidades e rotas PT-BR, configurações, UI, provedores de IA e migrations anteriores; nenhuma migração nova foi criada nesta consolidação.

## Implantação local no Docker Desktop (Windows)

**Não apague volumes Docker.** Não use `docker compose down -v`, `docker volume prune`, ou renomeie o projeto Compose de uma instância existente: os volumes de PostgreSQL, mídia, segredos e chaves de IA são persistentes e vinculados ao nome da stack.

1. Antes de substituir a pasta atual, faça backup do projeto e **dump do PostgreSQL**, com SHA-256 validado. Preserve os volumes de mídia e segredos e um método testado de restauração. O ZIP é um backup de código, **não dos dados**.
2. Extraia `alece/` do ZIP. Se a instalação anterior contém `.env` personalizado (hosts, HTTPS, porta, etc.), **preserve esse `.env`** e configure `ALECE_LOG_VALIDACAO=true` nele; não o sobrescreva com um `.env` local genérico. Em instalação nova, o `.env` fornecido já está pronto para `127.0.0.1:8088`.
3. Com o Docker Desktop em execução e na raiz do projeto, confira `docker compose config --quiet`. Então execute `docker compose up -d --build`.
4. Verifique `docker compose ps`, `docker compose logs --tail=100 web` e `src/logs/`. Faça login, conclua o setup caso necessário e teste `/configuracoes/`, `/visao-geral/` e troca de senha, sem enviar códigos de recuperação para logs ou capturas.
5. Para rollback de código, restaure a versão anterior da **pasta** e seu `.env` preservado, confira os checksums e reconstrua apenas o serviço web. Não reverta o banco sem checar se houve novas migrações e alterações de dados. Logs ficam preservados.

### Segurança do `.env`

O `.env` desta entrega **não contém senhas, segredos nem tokens pessoais**. O serviço `secrets-init` cria segredos internos no volume Docker `app_secrets` na primeira execução e mantém esses valores em reinicializações, desde que o volume não seja apagado. Nenhuma chave de API de terceiros é pré-configurada. Para publicar fora de `127.0.0.1`, revise hosts permitidos, TLS, cookies seguros, firewall e proxy reverso.

### Limites da validação desta distribuição

Foram realizadas verificações de sintaxe, teste isolado do middleware e teste local do logger sem banco. A verificação integrada com Docker, Django e PostgreSQL precisa ser realizada na máquina de destino. O healthcheck não substitui o teste funcional após login.


## Atualização complementar 2026-10-23 22:00

- Corrigido erro 500 ao abrir o gerenciamento de perfil financeiro.
- Adicionada opção de integração de IA **Personalizada**, com campos próprios para nome, endpoint e modelo.
- Reorganizadas as seções com tabelas para seguir o padrão visual unificado do ALECE.


- Ajustado alinhamento dos filtros de mês/categoria e padronizados seus tamanhos com os botões de ação.
- Reduzido o arredondamento dos atalhos de Visão geral para o mesmo nível dos botões do sistema.
- Padronizados checkbox, select, tabelas e seções de Configurações para o mesmo design do restante do ALECE.


- Centralizado o texto auxiliar das ações de seção ao lado do botão de adicionar.
- Removido o gradiente dos botões auxiliares e atalhos da visão geral.
- Adicionado respiro interno nas tabelas gerais e nas tabelas de Configurações.
- Compactado o filtro de Histórico por período para seguir o padrão do filtro de mês.


- Embutido o título **Resumo** e o botão de editar dentro do próprio cartão de resumo.
- Removido o rótulo **Evolução financeira** das seções de gráfico.
- Embutido o título **Metas** dentro do próprio cartão e removido o texto explicativo redundante da subseção.
