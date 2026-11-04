# ALECE

Plataforma de finanças pessoais/familiares livre, self-hosted (GNU GPLv3), com Django 5.2, PostgreSQL 16 e Docker Compose. Não transmite dados financeiros a terceiros nem exige proxy reverso, certificados ou serviços em nuvem.

## Instalação do zero

1. Instale Docker Engine/Desktop com Docker Compose **v2.24.0 ou superior**.
2. Extraia o ZIP, abra o terminal na pasta `alece` e execute:

   ```sh
   docker compose up --build -d
   ```

3. Na própria máquina, abra http://127.0.0.1:8088/configuracao-inicial/ e informe **nome de usuário, senha e confirmação**.
4. O ALECE cria automaticamente núcleo **Pessoal** e perfil **Principal**, com renda não informada; depois entre por `/entrar/`.

O serviço `web` agora usa `pull_policy: build` para impedir a reutilização silenciosa de imagens antigas. Em ambientes já instalados, não use `docker compose down -v`; antes de qualquer migração, faça backup validado dos volumes e do PostgreSQL. Em Windows/PowerShell, utilize `scripts/TECH_ALECE_Corrigir_Loop_Startup.ps1` para backup, reconstrução e verificação.

O Compose gera as credenciais internas no volume persistente `alece_app_secrets`, cria o banco, aplica as migrações e sobe o serviço. **O ZIP não distribui `.env`**: o `web` carrega os padrões não secretos de `.env.example` e sobrepõe, quando existir, as configurações locais de `.env` (Compose v2.24+). O Compose também lê automaticamente `.env` local para interpolar parâmetros como IP/porta; se ele não existir, usa os padrões `${...:-...}` do `compose.yaml`. Para personalizar, copie `.env.example` para `.env` e edite-o; nunca substitua o `.env` de uma instalação existente durante uma atualização. A senha do Administrador é escolhida pelo usuário e não é gerada automaticamente.

## Conferir a versão da interface em execução

O texto exibido na coluna **Categoria** de **Visão geral → Este mês** deve ser
**Previsível**, **Imprevisível** ou **Aplicação**. Os valores internos
`recurring`, `unexpected` e `application` permanecem apenas como identificadores
de operações. Uma captura com rótulos em inglês, quando o ZIP contém os rótulos
traduzidos, indica que a instância acessada pode estar servindo uma versão antiga.

Na instalação que você pretende atualizar, confira primeiro `docker compose ls`
e `docker compose ps` para evitar atingir outra instância. Após fazer backup
verificado dos dados e configurações conforme o RUNBOOK, extraia a versão nova
**sem substituir seu `.env`**, então execute na pasta correta:

```sh
docker compose up -d --build --force-recreate web
docker compose exec -T web grep -o item.kind_label /app/src/view/templates/finance/workspace_page.html
```

A segunda linha deve encontrar `item.kind_label` no template efetivamente
presente no contêiner. Confira também os logs e o healthcheck, entre na rota
`/visao-geral/` e force o recarregamento no navegador. Se o marcador não
aparecer, confirme o diretório, o projeto Compose, o contêiner acessado e a
porta antes de qualquer outra intervenção. **Não use `down -v` nem substitua
volumes.** O teste do template no contêiner não substitui testes autenticados.

## Conferir a tela de Investimentos após atualizar a instalação

A versão do wireframe tem o marcador `wireframe-r2-20261104` no template
`src/view/templates/finance/_goal_panel.html`. Se a tela ainda exibir os
quatro cartões antigos com apenas valores de posições, o contêiner servido
na porta 8088 ainda não contém a interface atualizada.

1. Identifique a pasta de instalação correta e confira `docker compose ls`,
   `docker compose ps` e `docker compose config --services`. Não confunda a
   pasta de downloads com a pasta que contém o `compose.yaml` da instalação.
2. Faça backup verificável antes de substituir código, conforme o RUNBOOK.
   Extraia o ZIP atualizado diretamente nessa pasta, sem substituir `.env`
   nem arquivos locais de dados ou credenciais.
3. Recrie exclusivamente a imagem web, preservando banco e volumes:

   ```sh
   docker compose up -d --build --force-recreate web
   ```

4. Confira o template **realmente dentro do contêiner**:

   ```sh
   docker compose exec -T web grep -F 'wireframe-r2-20261104' /app/src/view/templates/finance/_goal_panel.html
   ```

   Deve aparecer o atributo `data-alece-investments-ui`. Se não aparecer,
   confirme a pasta em que o comando foi executado, o contêiner ativo e
   a instância que responde em `http://127.0.0.1:8088/investimentos/`.
5. Após confirmar que o contêiner contém a versão nova, atualize a página
   usando Ctrl+F5. **Não execute `docker compose down -v` nem apague volumes.**

A marcação no template confirma a versão do arquivo, mas não substitui
homologação autenticada com Django, PostgreSQL e os dois temas.

## Validação integrada isolada (Windows e Linux)

Após instalar o Docker Compose v2.24+, execute **sem apontar para o Compose de produção**:

```sh
python scripts/Validar-ALECE-Isolado.py
```

O executor utiliza `compose.validation.yaml` em um projeto aleatório `alece_val_isolado_*`,
sem `container_name` fixo, portas publicadas, volumes externos nem parâmetros de `.env` local.
Ele confere a sobreposição opcional de `.env` **apenas em diretório temporário com valores
sintéticos**, constrói a imagem web, inicializa PostgreSQL isolado, verifica healthchecks,
configurações/migrations e persistência de um registro sintético e dos segredos após `down/up`.
Depois executa `compose.audit.yaml` em **outro projeto isolado** para a suíte de testes.
Evidências são gravadas em `~/test-results/alece_val_isolado_*/resultado.json`, além dos
relatórios da suíte quando disponíveis; o status é também registrado em `~/logs/`.
O executor faz `down` sem `-v`, preservando os volumes
de teste para investigação; ele nunca usa `compose.yaml` para iniciar ou parar serviços.
A opção `--skip-suite` pula exclusivamente a suíte Django, mantendo a checagem operacional.
Sem Docker local ou caso haja falha, o resultado é bloqueado, não aprovado.

**Atenção:** o Compose de produção ainda possui nomes fixos de contêiner. `-p` **sozinho**
não isola `compose.yaml`; para testes use exclusivamente o arquivo de validação.

## Estrutura

```text
alece/
├── docs/                 # arquitetura, relatórios, protótipo, changelog e contribuições
├── src/
│   ├── model/            # domínio puro: Decimal, cálculos e planejamento
│   ├── view/             # templates Django, CSS, JS e recursos visuais
│   ├── controller/       # apps Django core/finance, ORM, services, urls e config
│   ├── web.py            # rotas HTTP globais e adaptador URLconf Django
│   ├── logs/             # arquivos por execução, com ALECE_LOG_VALIDACAO=true
│   └── requirements/     # dependências e lockfiles com hashes
├── tests/                # testes unitários, integração e regressão
├── .staticfiles/         # gerado pelo collectstatic (não versionado)
├── media/                # volume persistente de uploads (não versionado)
├── docker/               # Dockerfile, boot e inicialização de secrets
├── scripts/              # scripts operacionais e auditoria
├── compose.yaml
├── .env                   # opcional, local, não distribuído
├── .env.example
├── .gitattributes
├── .gitignore
├── README.md
├── RUNBOOK.md
├── AGENTS.md
└── LICENSE
```

Django implementa arquitetura MVT; aqui o padrão MVC é aplicado por responsabilidade sem quebrar nomes de apps nem o histórico de migrações. Consulte [Arquitetura](docs/ARCHITECTURE_MVC.md).

## Desenvolvimento e contribuições

Consulte [Contribuir](docs/CONTRIBUTING.md), [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md), [docs/DOMAIN.md](docs/DOMAIN.md) e [AGENTS.md](AGENTS.md). A referência visual está em `docs/prototype/ALECE_Prototipo_Visual_v1.32.1.html` (somente comparação). Não presumir paridade visual enquanto não houver validação lado a lado.

## Segurança, dados e limitações

- O primeiro cadastro só deve ocorrer com publicação em loopback (`ALECE_BIND_IP=127.0.0.1`); não exponha instância vazia antes de criar o Administrador.
- Por padrão, HTTP somente no próprio host. Para NAS/LAN/VPS, configure rede, autenticação, firewall, `ALECE_ALLOWED_HOSTS` e proxy externo opcional em `.env` antes de publicar.
- **Não execute `docker compose down -v`: isso remove volumes persistentes**; `docker compose down` sem `-v` os mantém.
- Faça backups próprios do PostgreSQL e do volume de mídia, verificando SHA-256 e restauração isolada.
- A stack usa o nome `alece` e novos nomes de volume (`alece_app_pgdata`, `alece_app_media`, `alece_app_secrets`); não reaproveita automaticamente `alece-mvc_*` ou `alece_dbdata`. Se já existir um projeto Compose chamado `alece` no mesmo Docker, **não execute `up` antes de identificar os recursos associados e planejar o isolamento**, pois poderá afetar containers existentes.
- Para migrar uma instalação ALECE preexistente, não reutilize volumes sem ensaio: consulte [RUNBOOK.md](RUNBOOK.md).
- Ainda não houve execução de Docker ou da suíte PostgreSQL neste ambiente de empacotamento. Consulte [validação](docs/REORGANIZATION_VALIDATION.md).

Licença: [GPL-3.0-only](LICENSE).

## Navegação e tema por usuário

As rotas principais são `/visao-geral/`, `/despesas/`, `/investimentos/`,
`/movimentacoes/` e `/configuracoes/`. IDs de núcleos permanecem apenas em
URLs internas e legadas de edição/serviços; a navegação pública resolve o núcleo
ativo pela sessão autenticada e verifica sempre a associação do usuário.
Em caso de participação em vários núcleos, `/` permite selecionar qual usar.

O tema Claro/Escuro é persistido no campo existente `core.UserProfile.theme`
(PostgreSQL) via `POST /preferencias/tema/` com CSRF. A preferência do banco é
renderizada diretamente no HTML antes do carregamento do CSS, e o cache
`localStorage` é identificado pelo usuário para evitar vazamento entre contas.
Ao entrar por outro dispositivo, o tema vem do PostgreSQL.

## Configurações por papel e API de IA (2026-10-23)

Ver `docs/CONFIGURACOES_PERMISSOES_IA_2026-10-23.md` para permissões, rotas, integração externa opt-in, migração e rollback.

## Logs de validação por execução (2026-10-23)

O arquivo distribuído `.env.example` define `ALECE_LOG_VALIDACAO=true`; um `.env` local pode sobrescrever esse padrão. Quando ativo, **cada inicialização/reinício do serviço web via Docker Compose** salva stdout/stderr em um arquivo `src/logs/YYYY-MM-DD_HH-MM-SS.log` (horário UTC), sem parar a exibição normal pelo Docker. Desativar a opção não remove os arquivos antigos. Logs podem conter dados privados e não devem ser versionados ou publicados. Os containers continuam usando usuário não-root e o bind mount precisa ser gravável.

A regressão HTTP 500 na rota `/visao-geral/` foi corrigida: `workspace_page` agora retorna `HttpResponse` em todas as seções. Confira a correção funcional com login após reconstruir a imagem, não apenas com `/saude/ativo/`.

Configuração, validações, permissões e rollback: [docs/LOGS_VALIDACAO.md](docs/LOGS_VALIDACAO.md).

### Consistência visual e experiência responsiva (23/10/2026)

As interfaces de Configurações, tabelas, formulários, marca e favicon usam o mesmo
sistema visual claro/escuro do site institucional. Os formulários administrativos
de criação/edição abrem em modal com fallback de página completa; a autorização é
mantida no backend. Consulte `docs/UX_CONSISTENCIA_RESPONSIVA_2026-10-23.md` antes
de implantar sobre um banco existente.

## Recuperação obrigatória e gerenciamento de usuários (2026-10-23)

No primeiro acesso, cada usuário precisa gerar seis códigos únicos de recuperação, copiar, baixar o arquivo TXT e confirmar o armazenamento antes de usar o sistema. Os códigos não ficam legíveis no banco e cada código só pode ser usado uma vez. A troca de senha e os controles de usuários são feitos via modais. Leia [docs/RECUPERACAO_USUARIOS_2026-10-23.md](docs/RECUPERACAO_USUARIOS_2026-10-23.md) para implantação, segurança, testes e rollback.

## API de IA e URLs em português (23/10/2026)

A integração de IA possui presets e aceita somente o token do provedor escolhido. Os tokens são mantidos no volume Docker `app_ai_tokens`, fora do PostgreSQL. Os três destinos (despesas, investimentos, movimentações) são habilitados automaticamente; análises exigem consentimento a cada solicitação. O modal de Perfis reúne edição e permissões. As rotas públicas usam português ASCII, com aliases antigos para compatibilidade. Consulte `docs/ATUALIZACAO_IA_PERFIS_ROTAS_2026-10-23.md`.


## Gestão de usuários e visual unificado (23/10/2026)

Veja `docs/GESTAO_USUARIOS_UI_2026-10-23.md` para desativação, exclusão por anonimização com auditoria preservada, visual responsivo e recuperação. Esta distribuição completa inclui somente `.env.example`, com `ALECE_LOG_VALIDACAO=true`; `.env` permanece opcional e local.

## Verificação de inicialização (2026-10-24)

O contêiner verifica segredos, configuração Django, migrações aplicadas, rotas,
templates, arquivos estáticos, banco, tabelas e volumes antes de iniciar o Gunicorn.
O healthcheck de Docker usa `/saude/pronto/`, incluindo consulta SQL read-only.
Falhas críticas interrompem a inicialização, com log em `src/logs/` quando ativo.

A suíte de testes completa é executada **separadamente** em banco isolado na CI;
ela não roda em cada inicialização para não comprometer dados nem disponibilidade.
Para executar a validação local que independe do banco:

```bash
bash scripts/verify.sh
```

Consulte `docs/TESTES_E_INICIALIZACAO_2026-10-24.md`.

## Containers, testes e evidencias (2026-10-25)

Os servicos Compose continuam `web`, `db` e `secrets-init`, mas seus nomes visiveis no Docker foram padronizados como **`alece_web`**, **`alece_db`** e **`alece_secrets_init`**. Nao ha quarto servico `app`; no momento, a propria aplicacao Django e o servico `web`. O `secrets-init` e um job one-shot: parar com codigo de saida zero e esperado, pois so gera/lê arquivos secretos persistidos e habilita o inicio de `db` e `web`.

Apenas renomear containers os recria na proxima operacao `docker compose up -d`. Nao renomeie os servicos, redes ou volumes. Preserve antes `.env` e dump validado do PostgreSQL, e **nunca** use `docker compose down -v`. Nomes fixos limitam a uma replica por servico e impedem executar duas stacks ALECE com esses nomes no mesmo daemon Docker.

Os resultados das validacoes de STARTUP ficam em `src/logs/YYYY-MM-DD_HH-MM-SS.log` quando `ALECE_LOG_VALIDACAO=true`. Esses resultados **nao** significam que a suite pytest rodou. A suite pytest roda no GitHub Actions e agora publica um arquivo JUnit `alece-pytest-results/pytest.xml` como artefato. Para um diagnostico de runtime read-only no Windows: `powershell -NoProfile -File .\scripts\Relatorio-Validacao-ALECE.ps1`; ele registra tudo em `%USERPROFILE%\logs\YYYY-MM-DD_HH-MM-SS.log` e NAO altera o banco.

Leia `docs/NOMES_CONTAINERS_VALIDACAO_ESTADO_2026-10-25.md` antes de implantar.


## Suíte de qualidade e resultados verificáveis (2026-10-27)

A suíte funciona em PostgreSQL de testes isolado. O comando Windows é
`./scripts/Executar-Testes-Isolados.ps1`. O log fica em
`$env:USERPROFILE\logs\YYYY-MM-DD_HH-MM-SS.log`, e JUnit/relatório HTML em
`$env:USERPROFILE\test-results\alece-...`. A pipeline também executa
Chromium em um job distinto e arquiva as evidências.

Consulte `docs/qualidade/ESTRATEGIA_TESTES_2026-10-27.md` e
`docs/qualidade/evidencias/rastreabilidade/` para a matriz de riscos e
resultados *efetivamente executados*.
