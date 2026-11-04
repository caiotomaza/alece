# Verificação técnica — 2026-10-23

## Escopo

- Cinco rotas públicas sem ID do núcleo.
- Seleção de núcleo validada por associação ativa e sessão de usuário.
- Sidebar com somente os cinco destinos; senha e recuperação na página Configurações.
- Ícone de informação para página institucional.
- Preferência Claro/Escuro por usuário persistida em `UserProfile.theme`, propagada por HTML
  antes de CSS e cache `localStorage` com escopo de usuário.
- Projeto Docker Compose `alece`, `src/requirements`, `docs/prototype`.

## Validações de fato executadas

- `python -m compileall -q src tests manage.py`: compilação sintática aprovada.
- `node --check src/view/static/finance/alece.js`: JavaScript aprovado.
- `python -m unittest discover -s tests -p 'test_*structure.py' -v`: 10/10.
- `node` com sandbox mínimo de DOM e `fetch`: alteração no DOM, cache por usuário,
  requisição POST com CSRF e sincronização ao servidor; aprovado.
- `yaml.safe_load(compose.yaml)`: válido, nome `alece` e serviços encontrados.
- Integridade do ZIP: verificação CRC e SHA-256 após o empacotamento.

## Testes incluídos e não executados neste ambiente

`tests/test_public_navigation_theme.py` contempla as cinco rotas, troca de núcleo,
isolamento, persistência do tema no banco, segundo navegador e segurança de POST.
Não foram executados pois não há Django/PostgreSQL instalados no ambiente.
Docker Compose, build, migrações, regressão integral e navegador com interface
real também **não foram executados** e exigem validação no host com Docker.

## Segurança de migração e operação

A mudança do nome Compose de `alece-mvc` para `alece` não migra volumes e pode
colidir com outro projeto chamado `alece`. Fazer inventário de `docker compose ls`
e backup validado antes de executar contra ambiente com dados. Não usar
`docker compose down -v`. URLs antigas em `/finance/` permanecem funcionais
para compatibilidade, mas os links principais usam rotas sem IDs.
