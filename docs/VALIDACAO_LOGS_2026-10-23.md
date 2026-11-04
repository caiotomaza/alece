# Verificação da alteração: logs por execução e HTTP 500

## Evidência inicial

No log fornecido pelo usuário em 23/10/2026, o PostgreSQL ficou `Healthy`, as migrações avançaram até `core.0007_ai_integrations... OK` e o Gunicorn iniciou. A requisição autenticada `GET /visao-geral/` retornou HTTP 500 com `ValueError: The view apps.finance.public_routes.public_page didn't return an HttpResponse object. It returned None instead.`

A causa comprovada na inspeção do código era um `return render(...)` ao final de `apps.finance.views.workspace_page` indentado exclusivamente dentro da condição de seções `expenses`, `investments` e `movements`. O retorno foi movido para o escopo da função; dessa forma a seção `overview` também recebe `HttpResponse`.

## Alterações locais do pacote

- `src/logs/.gitkeep` foi adicionado para manter o diretório de logs no projeto.
- `.env` recebeu `ALECE_LOG_VALIDACAO=true`; `.env.example` recebeu `ALECE_LOG_VALIDACAO=false`.
- `docker/logged_start.py` foi adicionado ao ponto de entrada do container; ele duplica stdout/stderr em um log exclusivo com timestamp UTC por inicialização **apenas quando habilitado**. Sinais e códigos de saída são propagados; não há remoção automática dos logs.
- `compose.yaml` recebeu o volume bind `./src/logs:/app/src/logs` exclusivamente no serviço web.
- O formato de log de acesso do Gunicorn foi limitado a IP, hora, método, caminho sem query, protocolo, HTTP status e quantidade de bytes (sem cookies, referer ou parâmetros de URL).
- `settings.py` passou a incluir data/hora, severidade, PID e origem nas mensagens de logging do Django; o container continua não enviando mensagens para terceiros.
- `.gitignore` e `.dockerignore` protegem contra inclusão acidental de logs no Git e na imagem Docker.
- Documentação de uso/limitações disponível em `docs/LOGS_VALIDACAO.md`, `README.md` e `RUNBOOK.md`.

## Testes executados neste ambiente

- `python -m unittest tests.test_execution_logs -v`: **4/4 testes OK** (logger ativo, inativo, restart sem sobrescrita, retorno incondicional na view).
- `python -m pytest -q tests/test_execution_logs.py`: **4 testes OK**, com aviso de que o plugin pytest-django não está instalado neste ambiente.
- AST Python de todos os módulos do projeto: **127 arquivos analisados sem erro de sintaxe**.
- Parser YAML do `compose.yaml`: **válido**, contendo volume bind e serviço web esperado.
- `sh -n docker/start.sh`: **sem erro de sintaxe**.

**Não testado neste ambiente:** Docker Compose real, PostgreSQL real, suíte completa Django e HTTP 200 autenticado. O código precisa de validação funcional no computador do operador. A criação dos logs no bind mount do Docker Desktop Windows também exige verificação de permissões.

## Aplicação, escopo e reversão

O ZIP anterior do ALECE foi arquivado e verificado por SHA-256 antes da intervenção no ambiente de construção. No computador de destino, faça seu próprio backup integral de configurações relevantes e dump PostgreSQL com SHA-256 **antes** de substituir o código. Preserve volumes existentes, inclusive secrets e mídia. Não execute `docker compose down -v`.

Para rollback de código, restaure o ZIP anterior verificado e reconstrua somente o serviço web; não descarte dados/volumes, e não reverta o banco sem avaliar migrações e dados posteriores. Logs gerados não devem ser eliminados automaticamente.
