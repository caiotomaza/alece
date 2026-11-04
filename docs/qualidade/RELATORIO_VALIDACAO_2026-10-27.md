# ALECE — Relatório de auditoria de testes (27/10/2026)

## Escopo executado

A base é **exclusivamente** `ALECE_COMPLETO_Estabilizacao_Funcional_2026-10-27.zip` (SHA-256: `463d398030f74f81bb70c862eff45b676b77f2e758d2d14cc86a9971b2a8c10d`). Nenhuma migration, operação financeira, fluxo de produção ou dado financeiro real foi alterado.

### Alterações

- Adicionados `scripts/quality/test_environment.py`, `run_suite.py` e `report_tests.py` para controle de execução isolada, logs e evidência JUnit/HTML/CSV/JSON.
- O `pytest` exige `ALECE_TEST_ISOLATED=1`, nome de banco explicitamente de teste e host local/isolado. A CI e o Compose audit receberam as respectivas variáveis.
- Os testes existentes de Logs e IA foram **movidos**, sem remover casos, para `tests/logs` e `tests/integrations`.
- Adicionadas verificações de autorização HTTP de usuário comum/admin, falso POST em configuração de IA, e isolamento do ambiente de QA.
- Implementadas jornadas Playwright de páginas principais, seleção de perfil, autorização e página administrativa mobile em `tests/browser`.
- CI reorganizada com jobs independentes `python` e `browser`, ambos usando instâncias separadas de PostgreSQL 16 e JUnit; os artefatos são publicados também após falha.
- O diagnóstico PowerShell copia logs, XML, HTML e CSV do container de testes para o HOME do usuário e **não remove** os containers para permitir investigação.
- Acrescentado arquivo `src/requirements/browser.in` apenas para testes; dependências de produção e locks não foram alterados.
- Adicionados artefatos locais verificáveis em `docs/qualidade/evidencias`, incluindo matriz de casos de teste e resultados.

### Resultados reais nesta sessão

| Categoria | Resultado | Evidência |
|---|---|---|
| Testes unitários e estruturais locais, independentes de Django | **21 aprovados**, 0 falhas, 0 ignorados | `evidencias/testes_locais_sem_banco.xml` e `.log` |
| Análise sintática Python de código + testes + scripts | **Aprovada** | log de intervenção |
| YAML da CI e Compose (parser PyYAML) | **Aprovado** | log de intervenção |
| Isolamento da configuração de teste | **Aprovado nas verificações estáticas e 8 casos parametrizados** | JUnit |
| Suíte Django/ORM/PostgreSQL integral | **NÃO EXECUTADA** | Django, psycopg e Docker ausentes no runtime desta sessão |
| Jornadas Playwright reais | **NÃO EXECUTADAS** | não havia Django/pytest-django nem servidor PostgreSQL |
| Métricas de cobertura | **NÃO MEDIDAS** | sem execução completa instrumentada |

O `pytest` local registrou **um aviso**: a opção `DJANGO_SETTINGS_MODULE` não foi reconhecida porque `pytest-django` não está instalado aqui. Ele **não** foi interpretado como aprovação ou falha dos testes de banco.

A matriz AST da entrega identifica **479 funções de teste** (15 funções efetivamente exercitadas pelo JUnit local, gerando 21 casos, e 464 funções não executadas). Funções declaradas e casos reais executados não são intercambiáveis, e a diferença não é porcentagem de cobertura.

## Pendências para homologação

1. Executar o Compose isolado com PostgreSQL 16 e Python 3.12 para verificar todas as migrações, CRUD, estornos, importações e autorização.
2. Executar o job Playwright real em Chromium; analisar prints e traces dos cenários reprovados.
3. Revisar manualmente as falhas reais, corrigir causas e repetir toda a regressão; **não apagar testes antigos nem atualizar evidências só para passar**.
4. Validar explicitamente concorrência financeira com transações reais e eventual deadlock; não se pode inferir segurança concorrente da sintaxe do código.
5. Expandir a matriz de autorização para todas as combinações de grants por módulo e operações de importação/exportação. A suíte tem diversos casos, mas a execução completa é indispensável.

## Política de aprovação

Um release é bloqueado se Django/pytest ou Playwright falhar, se o teste não puder ser executado ou se o isolamento do banco for inconclusivo. Este pacote **não está homologado para implantação de produção** pelo resultado local.

## Recuperação

O backup de configuração prévia foi criado em `HOME/backups/` com SHA-256 validado antes das alterações. Para rollback, restaure a versão anterior dos arquivos de testes/CI/Compose/scripts. Como não houve migrations, o esquema não precisa ser revertido. Conservar os logs, backups e relatórios existentes.
