# Arquitetura MVC adaptada ao Django

Django é naturalmente MVT (Model-View-Template). A organização por pastas solicitada é uma **separação de responsabilidades**, não renomeação arbitrária de classes Django.

- `src/model/finance/domain`: domínio puro, `Decimal`, cálculos e planejamento independentes do ORM.
- `src/view/templates`: HTML Django; `src/view/static`: CSS, JS e Chart.js local.
- `src/controller/apps/core`: autenticação, identidade, autorização e auditoria.
- `src/controller/apps/finance`: apps, models ORM, migrations, formulários, URLs, serviços transacionais e controllers HTTP.
- `src/controller/config`: settings, roteamento raiz, ASGI/WSGI.
- `src/requirements`: lockfiles de produção e desenvolvimento para builds reproduzíveis.
- `tests`: suíte existente de integração e regressão.
- `.staticfiles/`: gerado na imagem com `collectstatic`; `media/`: arquivos de upload em volume.
- `docker`: imagem, inicialização de segredos e entrypoint; `compose.yaml` na raiz.

## Compatibilidade

As importações `apps.core`, `apps.finance` e `config` e os labels das apps `core`, `finance` foram preservados; seus arquivos são encontrados por `PYTHONPATH=/app/src/controller:/app` no Docker, pelo `manage.py` e por `pyproject.toml` no Pytest. Não renomear labels de apps nem apagar migrações de bases persistentes. `apps.finance.domain.*` continua disponível por wrappers para compatibilidade, enquanto a implementação pura está em `src.model.finance.domain`.

A camada transacional mantém a escrita financeira em serviços e auditabilidade no PostgreSQL. Não usar a divisão MVC como justificativa para escrever dados diretamente no template ou na view.

## Segurança do Compose

O projeto Compose é denominado `alece`. Os volumes lógicos `app_pgdata`, `app_media`, `app_secrets` evitam reutilizar automaticamente os nomes antigos `alece_dbdata` e `alece-mvc_*`. Mudar o nome de projeto no mesmo Docker pode afetar outra stack denominada `alece`; verificar primeiro.

`docker compose up` inicia `secrets-init`, que gera credenciais exclusivas e persistentes no volume `app_secrets`, antes de iniciar PostgreSQL e web. Nenhum segredo fixo é distribuído no `.env`. O initializer não substitui segredos já existentes. Todos os volumes são persistentes; `docker compose down -v` não é procedimento de manutenção. Para LAN ou proxy reverso, definir bind e hosts confiáveis no `.env`; primeiro cadastro deve ocorrer pelo bind loopback antes de expor serviço.
