# ALECE — Estratégia de testes e rastreabilidade (27/10/2026)

## Objetivo e fronteira

A suíte atual é organizada por domínio em `tests/{auth,configuration,finance,imports,reports,operations,ui,logs,integrations,browser}`. Testes anteriores foram **preservados**, com realocação apenas dos testes de Logs e APIs de IA. Os testes existentes não foram substituídos por testes de string ou sintaxe mais fracos.

O ALECE é um produto Django self-hosted que manipula dados financeiros: toda suíte com banco deve usar PostgreSQL **sintético e isolado**, nunca volumes ou usuários reais. A presença de `ALECE_TEST_ISOLATED=1`, nome do banco de teste e host local é um bloqueio adicional; o verdadeiro isolamento também depende da infraestrutura (Compose sem env_file, porta pública ou volumes da aplicação). Não execute usando o Compose de produção.

## Camadas

| Camada | Escopo | Ferramentas | Evidência |
| --- | --- | --- | --- |
| Inicialização | pré-flight e consistência de settings/migrations | Django check + preflight | saída CI ou log isolado |
| Unitários | parsers, cálculos, regras sem dependências externas | pytest | JUnit e stdout |
| Integração | ORM, views, formulários, CRUD e saldo | Django TestCase/pytest + PostgreSQL 16 | JUnit |
| Segurança | usuários comuns, admins, tenants e requisições alteradas | cliente Django e ORM | JUnit |
| Navegador | navegação real e autorização entre páginas | pytest-playwright + Django live_server + Chromium | JUnit, screenshot/trace em falha |

A CI **não** possui acesso a credenciais ou banco de produção. Migrations são verificadas com `makemigrations --check --dry-run`. O job Python falha quando pytest ou estática falham; o job browser é independente, com Chromium e PostgreSQL próprios. Ausência de JUnit é marcada como NÃO EXECUTADO, jamais aprovada.

## Comandos

**Windows + Docker Desktop**, executar na pasta do ALECE:

`./scripts/Executar-Testes-Isolados.ps1`

A execução cria `HOME/logs/YYYY-MM-DD_HH-MM-SS.log` e copia os resultados para `HOME/test-results/alece-.../`; os containers de teste são preservados para análise. Não remova os volumes de produção. O PostgreSQL isolado do Compose não publica porta e não monta dados da instalação.

**CI**: o job `python` instala o lock de desenvolvimento com hashes e executa `scripts/quality/run_suite.py`, produzindo `test-results/pytest.xml`, `pytest.log`, `quality/index.html`, `quality/resumo.json` e `quality/rastreabilidade.csv`. O job `browser` instala as versões documentadas em `src/requirements/browser.in`, executa Chromium e arquiva evidências `test-results/browser.xml` e capturas em falhas. Artefatos são publicados até quando um job reprova.

**Matriz local**: `python scripts/quality/report_tests.py --root . --out test-results/quality --junit test-results/pytest.xml --junit test-results/browser.xml`

### Resultados e critérios de aceite

- `APROVADO`: somente quando um caso consta de JUnit de execução real.
- `FALHOU`: assertion ou erro durante a execução.
- `IGNORADO`: `skipped` explícito.
- `NAO_EXECUTADO`: ausente de JUnit; incluir aqui testes sem Django/PostgreSQL disponíveis.
- Funções de teste declaradas no AST **não** medem cobertura; parametrizações podem gerar vários casos por função.

Um caso sem evidência não deve ser aprovado, mesmo que o código compile. Sem aprovação dos jobs Python e browser, bloquear release. Bugs funcionais identificados devem receber teste que os reproduza antes de serem considerados resolvidos.

## Matriz de risco

| Módulo | Fluxos exigidos | Risco crítico | Evidência atualmente disponível |
| --- | --- | --- | --- |
| Autenticação | login positivo/negativo, recuperação, sessão, isolamento | sequestro de conta | testes em `tests/auth` |
| Configurações | perfil comum/admin, CRUD, perfis, último ativo | privilégio indevido / perda de perfil | `tests/configuration` |
| Finanças | CRUD, saldos, pagamento, transferência, estorno, idempotência | débito incorreto ou duplicado | `tests/finance` |
| Importações | arquivo inválido, revisão, confirmação, limites, permissões | gravar dados parciais | `tests/imports` |
| Relatórios | visualização, exportação, importação sem herdar permissões | vazamento ou corrupção | `tests/reports` |
| Logs | filtros, detalhe e exportação restrita | vazamento de auditoria | `tests/logs` |
| Integrações IA | seleção única, token, consentimento e permissão | compartilhamento não autorizado | `tests/integrations` |
| Interface | cinco rotas, seleção, desktop/mobile, temas, retorno | contexto de navegação perdido | `tests/ui` e `tests/browser` |
| Operações | preflight, logs, migrações e isolamento | rodar QA no banco real | `tests/operations` |

A matriz detalhada por teste, com status e evidência, é gerada em `quality/rastreabilidade.csv` e incluída parcialmente em `docs/qualidade/evidencias/` para a execução local desta entrega.

## Limitações atuais

A interface Playwright foi preparada para CI, mas **não executada neste ambiente de preparação** por falta de Django/pytest-django e PostgreSQL. Também não foi executada a suíte Django completa. Os testes de banco e navegador devem ser considerados **pendentes**, não aprovados. A cobertura percentual permanece **não medida**.

A etapa futura de regressão visual precisa acrescentar baselines revisados por humanos, comparações estáveis com fontes/sistema fixos, contrastes, zoom e leitor de tela. Testes de navegador atuais verificam principalmente navegação e isolamento; não equivalem a conformidade WCAG.

## Rollback

Se esta etapa provocar falhas, restaure os quatro arquivos de configuração a partir do backup SHA-256 criado antes da intervenção, e restabeleça os arquivos de teste/CI da versão anterior. Não há migrations ou mudanças de esquema. Se uma instalação foi modificada, só restaurar seus backups de banco/volumes após avaliar o impacto da implantação. Conservar logs e artefatos para diagnóstico.

## Laboratório de desempenho (adendo 27/10/2026)

O job manual `performance` da CI executa páginas Django com PostgreSQL efêmero e dados fictícios, produzindo JUnit/HTML e JSON apenas com métricas agregáveis. O contrato de consulta de estorno está em `tests/performance/test_movement_reversal_queries.py`. Sem evidência local de backend, status **NÃO EXECUTADO**; consultar `docs/performance/METODOLOGIA_E_RELATORIO_2026-10-27.md`.
