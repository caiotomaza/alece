# ALECE — Relatório de validação da Etapa 3

Data: 2026-10-27.

## Ambiente verificado

- Código extraído do ZIP integral da etapa 2; os arquivos pré-existentes não foram removidos.
- Python do ambiente de verificação: 3.13 (projeto Docker utiliza Python 3.12).
- `pytest`: disponível; `pytest-django`, `Django`, `psycopg`, servidor PostgreSQL, `psql` e `docker`: indisponíveis neste container.
- Banco real do usuário: não acessado. Nenhuma conexão externa com APIs de IA foi realizada.

## Execuções e evidências

| Ação | Resultado | Evidência |
|---|---|---|
| Backup integral de entrada e SHA-256 | APROVADO | HOME/backups/`YYYY-MM-DD_HH-MM-SS__alece-base.zip` e `.sha256` (container da auditoria) |
| Compilação sintática Python dos módulos e testes | APROVADO | `compileall` local |
| Testes locais sem banco: logs, arquitetura, guarda de isolamento, rotação/revogação de token, CSV | **24 aprovados** | `docs/qualidade/evidencias/seguranca_local_2026-10-27.xml` |
| Execução preliminar sem identificador de DB isolado | BLOQUEADA corretamente | Guardião recusa ausência de `ALECE_TEST_ISOLATED` |
| Execução preliminar de teste CSV com anotação de tipo ausente no namespace extraído | FALHOU inicialmente, teste de harness corrigido e reexecutado | Log da auditoria; resultado final JUnit é de 24 aprovados |
| Testes Django/PostgreSQL adicionados (autenticação, sessão, CSRF, IA, exportações e importação) | **NÃO EXECUTADO** | Dependências/serviços indisponíveis |
| Verificação `manage.py check --deploy` | NÃO EXECUTADO | Django indisponível |
| Revisão funcional via navegador/Playwright | NÃO EXECUTADO | Sem serviço Django/PostgreSQL |
| Migrations novas | NENHUMA | Verificação de drift pendente no Docker |
| Auditoria dinâmica contra endpoints expostos em produção | NÃO EXECUTADO | Não tocar ambiente do operador |

Um aviso local do pytest (`Unknown config option: DJANGO_SETTINGS_MODULE`) decorre da ausência de `pytest-django` no ambiente local e não deve ser interpretado como resultado dos testes Django.

## Suíte acrescentada

- `tests/auth/test_security_session_revocation_20261027.py`
- `tests/configuration/test_security_http_boundaries_20261027.py`
- `tests/integrations/test_ai_secret_lifecycle_20261027.py`
- `tests/imports/test_security_import_errors_20261027.py`
- `tests/reports/test_csv_injection_and_cache_20261027.py`
- `tests/operations/test_security_source_contracts_no_django.py`
- Atualizado `tests/auth/test_bootstrap_user_mgmt.py` para gerar sessões **assinadas reais** de Django.

## Condição de aceite

A etapa **não está homologada para produção** sem execução com PostgreSQL isolado e sem validação das permissões e da revogação real de sessões no backend instalado. Não há pontuação automática de segurança ou conformidade LGPD presumida.

Após executar a CI, utilize os relatórios JUnit de Django e browser publicados como artefatos. Qualquer falha de autorização, transação ou vazamento bloqueia o deploy.
