# Relatório técnico da reorganização

Fonte: upload `alece(1).zip` com código e relatórios locais; código mais recente deste upload, não da versão anterior do pacote.

Mudanças: separação física `src/model`, `src/view`, `src/controller`; manutenção dos app-labels e migrações; Compose automático com segredos persistentes; migração na inicialização; estáticos em `public/static`; mídia persistente em `public/media`; arquivos `.git`, `.env` de origem, backups, logs, uploads e caches locais não distribuídos.

Ambientes anteriores não foram acessados e seus volumes não foram alterados. Para migração de dados existentes, requer backup e ensaio isolado; não associar volumes antigos automaticamente ao novo projeto Compose.

O Docker não está instalado neste sandbox, portanto build, migrações PostgreSQL, testes de integração e disponibilidade HTTP devem ser validados na máquina de execução antes de considerar produção. A reorganização não equivale à homologação visual do protótipo v1.32.1.

O projeto Compose foi separado como `alece-mvc`, com volumes `alece-mvc_dbdata`, `alece-mvc_media` e `alece_app_secrets` para não colidir com instalações preexistentes do projeto `alece`.

## Ajustes de 23/10/2026 — organização e formulário

- Nome do projeto Compose: `alece` (anterior `alece-mvc`). Variáveis `-p`/`COMPOSE_PROJECT_NAME` têm precedência sobre o nome do arquivo.
- Volumes novos `alece_app_pgdata`, `alece_app_media` e `alece_app_secrets`: **não** reutilizam automaticamente os volumes anteriores. Ao executar a nova stack com nome `alece`, inspecione previamente se já existe outro projeto Docker com esse nome; as instâncias podem colidir em containers mesmo quando os volumes são diferentes.
- Dependências movidas de `requirements/` para `src/requirements/`, com Dockerfile, CI e Dependabot ajustados.
- Referência visual original preservada em `docs/prototype/`, sem diretório `reference/` na raiz.
- Materiais operacionais e de contribuição agrupados em `docs/`.
- A tela de primeiro acesso agora tem layout e estilos próprios em `src/view/static/core/setup.css`: campos verticais com largura 100%, labels acima dos inputs, foco acessível, responsividade e suporte a temas Claro/Escuro. Não foram adicionados campos de token nem de dados financeiros.
- Esta etapa não envolve alterações de banco ou migrações. Sem Docker neste ambiente de edição, execução da stack e regressão completa PostgreSQL não foram verificadas.

Nota atual (2026-10-24): caminhos antigos `public/static` e `public/media` foram migrados para `.staticfiles/` e `media/`; volume Docker `app_media` preservado.
