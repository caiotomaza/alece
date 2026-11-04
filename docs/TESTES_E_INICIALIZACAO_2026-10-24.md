# ALECE — Arquitetura e verificações de inicialização

## Princípio

Não existe teste que comprove “100%” do funcionamento de qualquer serviço.
Startup verifica pré-condições **sem modificar dados financeiros**;
a suíte de regressão testa comportamento em banco de testes isolado.
O Django recomenda `manage.py check` e o test runner cria seu banco de testes.

## Checks rápidos no início de cada container

A inicialização atual (`docker/start.sh`) executa, na ordem:

1. Presença dos segredos sem imprimir valores;
2. `manage.py check` (framework Django);
3. `manage.py migrate --noinput` (fluxo pré-existente: PODE ALTERAR O BANCO);
4. `manage.py migrate --check --noinput` (detectar pendências);
5. `manage.py alece_startup_check`: reverse/resolve de rotas, carregamento de templates,
   arquivos estáticos essenciais, `SELECT 1`, presença de tabelas dos módulos financeiros e administrativos e
   permissões de escrita em mídia/logs;
6. Inicia Gunicorn somente após essas validações.

O healthcheck do Docker consulta `/saude/pronto/`, que exige resposta do banco.
Se uma verificação crítica falhar, a inicialização é interrompida com erro
registrado pelo capturador quando ALECE_LOG_VALIDACAO=true.

## Atenção às migrações automáticas

O projeto herdou a aplicação automática de migrações. Em ambiente de produção,
ANTES de implantar versões com migrações, crie um backup consistente do PostgreSQL
com SHA-256 e valide-o, preserve volumes e configure rollback da versão anterior.
A implantação **não** realiza backup completo do PostgreSQL por conta própria.

## Testes completos (desenvolvimento e CI)

Rodam em banco de testes isolado configurado por `config.test_settings`, não como
parte do startup. Exemplos, no ambiente de desenvolvimento com dependências:

```bash
pytest -q tests/finance/
pytest -q tests/imports/
pytest -q tests/configuration/
pytest -q tests/reports/
pytest -q tests/ui/
pytest -q tests/operations/
pytest -q tests/      # suíte completa
```

Abas e comportamentos prioritários: autorização, login/recuperação de conta,
CRUD de perfis/contas/despesas/investimentos, integridade de lançamentos, importação
CSV/OFX/PDF, relatórios, permissões, renderização e rotações de tema, geração e
restauração de backup, diagnóstico de logs e rotas.

Os arquivos `test_sprint*` e as demais suítes antigas foram realocados e
renomeados por domínio; o corpo e as verificações dos testes anteriores foram
preservados. Acrescentados testes de rotas, renderização e inicialização.

## Rotas

`src/web.py` registra todas as rotas web globais por `WebRoutes.build()`.
`config/urls.py` é um adaptador para `ROOT_URLCONF` oficial do Django.
Includes por aplicação (`apps.core.urls`, `apps.finance.urls`) foram preservados
para compatibilidade, nomes e segurança.

## Armazenamento

A antiga pasta `public/` foi retirada do código. `collectstatic` passa a usar
`.staticfiles/` (artefato gerado), enquanto a mídia usa `media/`, montada no
MESMO volume Docker `app_media` existente. Não apague nem reinicialize volumes.
Em instalações com bind mounts personalizados, atualize o caminho antes de subir.

## Rollback

Restaure os arquivos do backup validado e faça deploy da versão anterior.
Se alguma migração do Django tiver alterado esquemas, use o plano de rollback da
migração e um backup consistente de banco. **Nunca use `docker compose down -v`.**
