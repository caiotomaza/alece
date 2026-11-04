# Logs de validação por execução (ALECE)

## Objetivo

O ALECE pode salvar **um arquivo de log para cada inicialização do serviço web** quando `ALECE_LOG_VALIDACAO=true` no `.env` da raiz do projeto. O arquivo registra o início da execução, as verificações de segredos (sem valores), o `manage.py check`, migrações, erros de inicialização, erros HTTP/tracebacks emitidos no console, saídas do Gunicorn/Django e o código de término. **A gravação é uma cópia do stdout/stderr; a saída continua acessível via `docker compose logs`.**

A pasta é obrigatoriamente:

```text
alece/
└── src/
    └── logs/
        ├── .gitkeep
        ├── 2026-10-23_19-45-01.log
        └── 2026-10-23_19-45-13.log
```

Os nomes seguem `YYYY-MM-DD_HH-MM-SS.log` com relógio **UTC do container**, não o fuso do computador. O gravador reserva o nome de forma exclusiva; uma inicialização muito próxima da anterior não sobrescreve nenhum arquivo. Os arquivos são persistidos no computador pelo bind mount `./src/logs:/app/src/logs`, sem utilizar o volume PostgreSQL.

## Configuração

No `alece/.env`, edite:

```dotenv
ALECE_LOG_VALIDACAO=true
ALECE_LOG_LEVEL=INFO
```

- `true`: salva um `.log` por início/reinício do serviço **web** (incluindo reinicializações automáticas).
- `false`: não cria novos arquivos de log em `src/logs`, mas mantém a saída normal do Docker e **não exclui** arquivos antigos.
- Nesta distribuição, **ambos os arquivos** `.env` e `.env.example` já incluem `ALECE_LOG_VALIDACAO=true`. Em uma instalação existente, preservar o `.env` local é importante; configure somente essa variável se seu `.env` tiver outras opções próprias.
- Mudanças no `.env` exigem recriar o serviço web; não basta recarregar a página do navegador. Em instalação já existente, confira o estado e o backup do banco antes de executar `docker compose up --build -d web`.

Para aplicar a versão nova em uma **instalação já existente**, preserve seu `.env` local (adicione apenas a variável se ela não existir), volumes de banco/secrets/mídia e faça um dump PostgreSQL com SHA-256 antes da primeira execução do novo código, pois o script de entrada roda migrações. Consulte `RUNBOOK.md`. Não use `docker compose down -v`.

Para consultar erros:

```powershell
Get-ChildItem .\src\logs\*.log | Sort-Object LastWriteTime -Descending | Select-Object -First 5
Get-Content (Get-ChildItem .\src\logs\*.log | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName -Tail 100
```

Os comandos acima são apenas de leitura, para Windows PowerShell. Para saída do Docker: `docker compose logs --tail=100 web`.

## Segurança, armazenamento e limites

- `ALECE_LOG_VALIDACAO` **não é** `ALECE_DEBUG`: mantenha `ALECE_DEBUG=false` em produção; não habilite páginas de traceback no navegador.
- O log não registra automaticamente senhas e variáveis de ambiente. O formato de access log exclui query string, referer, cookies e cabeçalhos. **Ainda assim** bibliotecas ou exceções podem incluir dados privados em mensagens; trate todo `.log` como informação sensível.
- Não publique `src/logs/` em Git, ZIP público, suporte aberto ou qualquer pasta servida pelo HTTP. `.gitignore` e `.dockerignore` excluem os arquivos `.log`; apenas `.gitkeep` mantém a pasta.
- O processo grava como usuário não privilegiado `app`. Em servidores Linux com bind mount, o dono/permissões do diretório do host precisam permitir escrita **sem** tornar a pasta pública. Se a montagem impedir escrita, a inicialização falha informando permissões em vez de omitir o log silenciosamente. No Docker Desktop para Windows, confirme a possibilidade de escrita e proteja o diretório por permissões NTFS.
- A gravação ocorre apenas no processo web iniciado pelo launcher em Docker Compose; comandos `manage.py` executados separadamente no host ou via `docker compose exec` não recebem, por padrão, um arquivo próprio.
- Não há rotação, limpeza ou envio a servidores externos automáticos. Cabe ao operador acompanhar o consumo de disco e definir uma retenção compatível com privacidade e auditoria. Desligar a opção não elimina registros já produzidos.
- `health/live/` retornando 200 significa apenas que o processo responde; valide as páginas reais (especialmente `/visao-geral/`).

## Validações e rollback

1. Verifique se `ALECE_LOG_VALIDACAO=true` está carregada pelo serviço web, sem imprimir segredos.
2. Faça uma inicialização, confirme `src/logs/YYYY-MM-DD_HH-MM-SS.log` e compare as linhas com `docker compose logs web`.
3. Faça login e abra `/visao-geral/` e as quatro outras rotas; a aplicação deve retornar HTTP 200 para o usuário autorizado.
4. Veja se o log apresenta `500`, `Traceback` ou `ERROR`. A correção do retorno `HttpResponse` em `workspace_page` está incluída nesta entrega.
5. Para rollback, restaure o ZIP anterior ou apenas os arquivos de código e Compose alterados, mantendo `.env` personalizado e os volumes persistentes. Logs anteriores permanecem na pasta; **não reverta o banco indiscriminadamente** após migrações ou novos dados sem um plano de recuperação.

A validação estrutural e o teste independente do gravador usam `python -m unittest tests.test_execution_logs -v`. A suíte Django completa requer dependências e banco de teste PostgreSQL isolado.
