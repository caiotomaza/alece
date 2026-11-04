# RUNBOOK — ALECE reorganizado

## Execução inicial

Na raiz do ZIP extraído: `docker compose up` (Docker Compose v2.24+). Não é necessário criar `.env` para a instalação inicial: os padrões não secretos vêm de `.env.example`. Se a instalação já possuir `.env`, preserve o arquivo local antes de substituir os arquivos do projeto. O serviço `secrets-init` gera e mantém segredos aleatórios no volume `alece_app_secrets`. O PostgreSQL aguarda essa etapa; a aplicação aguarda o PostgreSQL saudável e executa as migrações antes de subir o Gunicorn. Depois abra http://127.0.0.1:8088/configuracao-inicial/ e crie o primeiro Administrador com três campos. O login manual vem em seguida.

Por padrão, a porta da aplicação só é publicada em loopback. Não faça a primeira configuração através de um proxy remoto. **O código não embute TLS/proxy**; se desejar URL personalizada, use a infraestrutura de sua escolha, depois de cadastrar o Administrador pelo host e configurar `ALECE_BIND_IP`, `ALECE_ALLOWED_HOSTS`, `ALECE_CSRF_TRUSTED_ORIGINS` e as flags de proxy conscientemente. Não aceite cabeçalhos forwarded diretamente de clientes.

## Operações

- Ver status: `docker compose ps`
- Ver logs: `docker compose logs web` ou `docker compose logs db`; evite compartilhar saídas com credenciais ou dados pessoais.
- Parar sem remover volumes: `docker compose down`
- Reiniciar: `docker compose up -d` (não altera segredos do volume).
- Conferir migrações: `docker compose exec web python manage.py showmigrations`
- Validar Django: `docker compose exec web python manage.py check`
- Verificar saúde HTTP: `/saude/ativo/`, `/saude/pronto/`, `/saude/`

**Não execute** `docker compose down -v` em instalações com dados; o volume `alece_app_secrets` também guarda a senha que foi usada pelo banco PostgreSQL.

## Backup e recuperação

Os scripts operacionais `scripts/backup.sh`, `scripts/deploy.sh` e o assistente de recuperação PowerShell ainda exigem um `.env` local para a operação assistida. Na primeira utilização desses scripts, crie-o a partir de `.env.example` (ou utilize `scripts/bootstrap.sh` em Bash); não sobrescreva um arquivo já personalizado. `docker compose up` continua independente dessa etapa.


Faça e valide backups independentes do PostgreSQL e da mídia. Um arquivo SQL/dump válido deve ser ensaiado em **novo banco isolado**, com SHA-256 conferido, antes de qualquer recuperação. Não restaure SQL diretamente sobre um banco populado. Preserve volume de segredos junto do banco correspondente; perder esses segredos requer procedimento de recuperação de credenciais PostgreSQL e invalidação cuidadosa das sessões. Uma migração de schema pode exigir tratamento de dados legado: use preflight e testes em cópia antes de aplicar.

As instalações anteriores (portas 8000/8001/8002/8003) não foram modificadas por este pacote; não conecte os volumes antigos ao novo Compose automaticamente.

## Homologação isolada antes de atualizar uma instalação

Execute `python scripts/Validar-ALECE-Isolado.py` a partir da raiz, com Docker local e
Compose v2.24+. Em Windows, utilize `py -3.12 scripts/Validar-ALECE-Isolado.py` se o Python
3.12 estiver disponível. Esta ferramenta **não** usa `compose.yaml` para subir recursos:
usa `compose.validation.yaml` e, para testes, `compose.audit.yaml`, com namespaces aleatórios,
volumes dedicados e sem publicação de portas, nomes fixos ou acesso a dados de produção.
Rejeita contextos Docker remotos. Um teste de tabela exclusivo do PostgreSQL sintético
verifica persistência após `down`/`up`; a comparação dos hashes dos segredos permanece
em memória (seus valores não são exibidos).

O executor também valida separadamente a **interpolação de parâmetros** pelo Compose e a
**injeção no ambiente do contêiner**, usando um diretório temporário para simular `.env`
opcional. O `.env` real nunca é copiado, modificado ou injetado na stack de validação.
As evidências ficam no diretório local `~/test-results/alece_val_isolado_*/`; os volumes
de teste permanecem após `down`, sem `-v`, e requerem limpeza manual deliberada quando
não forem mais necessários. Nenhuma dessas operações acessa volumes de produção.

**Importante:** o `compose.yaml` normal contém `container_name` fixos, logo
`docker compose -p ... -f compose.yaml up` **não** é um teste isolado seguro.
A configuração de validação separada evita essa colisão. Sem execução de Docker,
os testes integrados devem ser marcados **NÃO EXECUTADOS**. Os jobs de navegador
continuam dependentes de `browser.in` até geração de `browser.lock` a partir de resolução
e instalação verificáveis com Python 3.12 e hashes; não inserir hashes estimados.

## Desenvolvimento

- Domínio puro: `src/model/finance/domain` (import antigo `apps.finance.domain.*` tem shims).
- Django apps e configuração: `src/controller/apps`, `src/controller/config`.
- HTML/CSS/JS: `src/view/templates`, `src/view/static`.
- Testes: `pytest -q` com PostgreSQL de testes isolado configurado; os testes do domínio puro também podem rodar sem servidor.
- CI: `.github/workflows/ci.yml` e `docker/Dockerfile`.
- Documentação anterior preservada em `docs/legacy/` apenas para consulta histórica; não aplicar comandos sem revisão.

## Alteração do nome do projeto Compose

Este pacote define `name: alece`. Se já existir outra stack Compose com nome
`alece` na máquina, examine `docker compose ls`, os volumes e seus backups
antes de executar; o nome da stack é o namespace de volumes/redes. Nunca use
`docker compose down -v` para tentar migrar bancos. A atualização de código
não migra dados automaticamente da antiga stack `alece-mvc`; planeje backup,
restauração verificada e rollback se a intenção for conservar seus dados.

## Tema e URL

A escolha de tema é gravada por usuário no PostgreSQL e aplicada nas telas de
login, recuperação, primeiro cadastro e páginas financeiras. A alteração é feita
no ícone da navegação; Configurações contém Alterar senha e Recuperação.
As cinco rotas públicas não exigem IDs de núcleo. Para múltiplos núcleos,
escolha o destino autenticado na página inicial.

## Captura local de logs por inicialização

Com `ALECE_LOG_VALIDACAO=true` em `.env.example` ou no `.env` local, cada execução do serviço web via Docker Compose gera um arquivo UTC em `src/logs/YYYY-MM-DD_HH-MM-SS.log`. O fluxo Docker permanece visível; desabilitar o parâmetro não apaga logs anteriores. **O recurso não liga `DEBUG` nem grava credenciais propositalmente.** Verifique permissões de escrita do volume bind e proteja os logs como dados privados. O Dockerfile inclui o launcher `docker/logged_start.py`; recrie a imagem para aplicar a mudança. Veja [docs/LOGS_VALIDACAO.md](docs/LOGS_VALIDACAO.md).

O erro 500 visto em `/visao-geral/` (view com retorno `None`) foi corrigido no fim de `apps.finance.views.workspace_page`. Teste a rota autenticada; `health/live/` 200 não garante que telas estejam funcionando.
