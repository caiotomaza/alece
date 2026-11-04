# ALECE — Configurações, permissões e integrações de IA

Revisão de 2026-10-23 baseada no pacote ALECE_Correcao_Loop_Startup_2026-10-23.zip.

## Rotas

A rota pública permanece `/configuracoes/`. Não inclui ID financeiro. A seleção do núcleo está na sessão e é sempre conferida no banco.

- `/configuracoes/`: cartão **Minha conta** para todo usuário. Cinco seções de administração (`Usuários`, `Perfis`, `API`, `Logs`, `Relatórios`) somente para administrador do núcleo atual.
- `/configuracoes/minha-conta/`: atualiza username, nome, sobrenome e e-mail, com confirmação da senha atual.
- `/configuracoes/codigos/`: status do código de recuperação sem revelar o valor, uma vez que o armazenamento pré-existente é um hash.
- `/password/change/`: alteração da própria senha, já protegida por senha atual.
- `/recovery/generate/`: substituição do código de recuperação anterior (código exibido **uma única vez** após confirmar a senha atual).
- `/configuracoes/api/nova/` e `/configuracoes/api/<id>/editar/`: metadados de integração por núcleo. Enviar dados só é possível via POST explícito e confirmação do administrador.

**Compatibilidade e limitação:** o mecanismo atual do ALECE suporta **um código** de recuperação ativo por usuário; não há recuperação em texto claro de códigos antigos e não foi introduzida uma falsa interface de múltiplos códigos. Ação de “resetar códigos” substitui esse único código. Migrar para conjunto de vários códigos exigiria alteração explícita no subsistema de autenticação.

## Autorização

Não confiar em esconder menus. Todas as views de administração exigem `WorkspaceMembership.Role.ADMIN` no workspace selecionado na sessão. Objetos são consultados com `workspace=workspace`; pessoas comuns não conseguem usar links diretos nem submeter POST administrativo. Nenhuma função de configuração administrativa é liberada com base apenas em `is_staff` ou `is_superuser` global.

Dados pessoais são alterados apenas pelo próprio usuário mediante senha atual. Configurações e análises de IA nunca alteram `TransactionBatch` ou `LedgerLeg`.

## API de IA (integração opt-in)

### Contrato configurado

O endpoint é uma API HTTPS **compatível com OpenAI Chat Completions** que aceite:

```http
POST /v1/chat/completions
Content-Type: application/json
Authorization: Bearer <chave_configurada_no_ambiente>
```

O corpo é JSON, com `model`, `messages` e `response_format: {"type":"json_object"}`. A mensagem do usuário contém JSON com este formato de dados, preparado com no máximo 40 registros já confirmados:

```json
{"schema_version":1,"section":"expenses","currency":"BRL","records":[{"date":"2026-10-01","description":"Compra","amount_brl":"-25.00","kind":"unexpected"}]}
```

A API deve responder JSON de Chat Completions com `choices[0].message.content` contendo JSON `{"summary":"..."}`. A resposta será recusada se inválida ou acima do tamanho permitido. A análise é armazenada por núcleo, perfil e seção e exibida nas páginas `despesas`, `investimentos` ou `movimentacoes` **somente para quem já tem permissão naquela área/perfil**. A saída é informativa; nenhuma classificação automática, edição de lançamento ou aconselhamento financeiro individual é realizada.

### Configuração de privacidade

Nenhuma integração habilitada na instalação limpa. Para autorizar uma integração de terceiro:

1. No ambiente do container `web`, configure `ALECE_AI_ALLOWED_HOSTS` com uma lista de hostnames HTTPS explícitos, como `api.example.com`. Nunca configure endereços internos ou redes privadas. No Compose atual, o arquivo `.env` particular é passado ao `web` via `env_file`.
2. Coloque a chave em uma variável de ambiente distinta que comece com `ALECE_AI_`, por exemplo `ALECE_AI_PROVIDER1_KEY`, **sem versionar o valor**. Não digite o valor na interface. Recomenda-se mecanismo de secrets do deployment para ambientes reais. A chave não é salva no PostgreSQL nem é incluída em logs de auditoria.
3. Na aba API, cadastre nome, endpoint completo, modelo, nome da variável, áreas habilitadas e marque a integração como habilitada.
4. O administrador deve selecionar o perfil, seção, marcar consentimento e acionar **Solicitar análise**. Nenhum envio em segundo plano foi implementado. O envio só inclui registros de importação marcados como confirmados, com data, descrição, valor e tipo — **não inclui o JSON bruto, memorandos, identificadores bancários nem credenciais**.

**Importante:** descrições de transações podem conter dados pessoais. O consentimento operacional deve ser respaldado pelo fundamento legal, política de privacidade e obrigações aplicáveis. Para privacidade total, não autorize host algum. O ALECE pode usar modelos self-hosted via futura integração explícita, mas esta revisão exige HTTPS confiável e não concede acesso HTTP a redes locais, para reduzir SSRF.

**Limitação funcional:** esta revisão usa análise manual de até 40 lançamentos confirmados; **não existe** análise automática a cada importação, fila, reprocessamento agendado ou suporte universal a qualquer API de IA. Outros protocolos devem receber adaptador e testes próprios.

## Logs e relatórios

- `Logs`: amostra de 12 eventos do núcleo, link para a lista detalhada já existente, respeitando permissões anteriores. Eventos sem workspace podem continuar indisponíveis a administradores locais.
- `Relatórios`: links para as ferramentas financeiras preexistentes e histórico de até 12 exportações do próprio núcleo.
- `Usuários`: tabela, criação/edição/gerenciamento de permissões com views antigas já protegidas no servidor.
- `Perfis`: tabela incluindo arquivados; CRUD e permissões via views preexistentes.

## Deploy e segurança de dados

**Não executar `docker compose down -v`**. Não substituir `.env`, volumes Docker, segredos ou dados da instalação. A nova migration é `core.0007_ai_integrations` e cria apenas as tabelas de integração e de análise.

Passos para Windows/Docker Desktop:

1. Guardar o ZIP desta revisão e **backup do projeto em uso**; copiar apenas arquivos de código alterados ou extrair em novo diretório mantendo `name: alece` e seu `.env` original. Em especial, preservar `app_pgdata`, `app_media`, `app_secrets`.
2. Antes de executar as migrações, ter um **dump lógico validado do PostgreSQL** e backup dos volumes secrets/media, com SHA-256 em `HOME/backups` e log em `HOME/logs` (o script `scripts/TECH_ALECE_Corrigir_Loop_Startup.ps1` realiza essas pré-verificações e backups quando executado a partir do pacote atualizado).
3. Verificar `docker compose config -q`. Reconstruir somente o web após o backup e aceitar as migrações, conforme script Windows já incluído.
4. Validar `docker compose ps`, health `web`, `python manage.py check`, `python manage.py showmigrations core`, rota `/configuracoes/` para cada papel e segurança dos endpoints administrativos.

Rollback do código: restaurar o ZIP anterior e reconstruir o web sem remover volumes. Como a migration cria tabelas, rollback para código anterior deve preservar as tabelas novas **ou** ocorrer mediante restauração consistente de dump em ambiente isolado. Nunca executar `migrate ... zero` ou excluir tabelas sem avaliação dos dados.

## Testes de validação

- `python -m unittest -v tests.test_navigation_structure` (sem Django): valida rotas base, links e tema.
- `tests/test_settings_roles_ai.py` (Django/PostgreSQL): verifica comum x admin, isolamento de núcleos, atualização de dados, recuperação, bloqueio de endpoints e consentimento. **A execução requer instância isolada de testes, com Django e banco disponíveis.**

Os testes reais de Docker, banco e requisição ao endpoint de IA não foram executados no ambiente de empacotamento. Não considerar aprovação funcional até testes em staging.
