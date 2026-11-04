# ALECE — Auditoria de desempenho e comparativo (2026-10-27)

## Escopo, ambiente e integridade

Base **exclusiva**: `ALECE_COMPLETO_REGRESSAO_VISUAL_PLAYWRIGHT_2026-10-27.zip`, com SHA-256 verificado antes da intervenção; o original está preservado em `$HOME/backups/`, junto ao `.sha256` validado. O trabalho altera uma consulta ORM e adiciona exclusivamente testes, CI e documentação. Nenhuma migration, índice, regra financeira ou integração externa é criada. `.env` e `.env.example` foram mantidos byte a byte.

Ambiente de preparação: Linux x86_64, Python 3.13.5, Node 22.16.0; Playwright Python/Chromium disponíveis. Sem Django, psycopg, servidor PostgreSQL ou DNS para instalar dependências. **Não foram iniciadas telas Django nem operações bancárias**. A CI declarada usa Python 3.12, PostgreSQL 16 efêmero e a imagem Playwright `v1.64.1-noble`.

## Resultado antes/depois — somente grandezas verificadas

| Medida | Antes | Depois | Evidência e interpretação |
| --- | ---: | ---: | --- |
| CSS/JS/SVG em `src/view/static`, soma dos bytes brutos dos arquivos | 443.936 B | 443.936 B | Contagem local; **não** é transferência de uma página |
| Compressão gzip nível 9 desses arquivos, somada individualmente | 122.073 B | 122.073 B | Gzip local determinístico, não equivale a cabeçalhos HTTP |
| LCP de páginas Django | Não medido | Não medido | Servidor ausente |
| CLS de páginas Django | Não medido | Não medido | Servidor ausente |
| INP de usuários reais | Não medido | Não medido | Exigiria coleta local de campo com decisão do operador; não incluída |
| Tempos HTTP e DOM das páginas | Não medido | Não medido | Medição CI preparada, primeira execução pendente |
| Número de queries SQL por movimentação | Não medido | Não medido | Teste ORM preparado; precisa de PostgreSQL e pytest-django |
| Tempo de tarefas humanas / conclusão / satisfação | Não medido | Não medido | Requer participantes; roteiro disponível |

**Nenhum ganho percentual alegado.** O teste `tests/performance/test_movement_reversal_queries.py` estabelece orçamento de uma consulta ao buscar três movimentações e suas relações de estorno: depende de execução real. No código anterior, `batch.reversal` acessado após `select_related('batch')` poderia emitir consulta adicional por batch; o novo `select_related('batch__reversal')` evita lazy loading dessa relação por meio de `LEFT JOIN`. O ganho e custo do join no PostgreSQL permanecem **não medidos**.

## Inventário e decisões

- Os scripts globais `alece.js`, `alece_modals.js` e `alece_accessibility.js` já são `defer` no shell. Não duplicar nem reordenar scripts sem testes de interação.
- Chart.js (~205 kB de fonte minificada) está restrito à página de relatórios que usa gráficos; **não** é importado em todas as rotas. O arquivo `.map` (~953 kB) não é solicitado pelo HTML e não deve ser contabilizado como transferência de usuário comum.
- CSS ativo foi consolidado em etapas anteriores; sua remoção ou fusão requer teste visual Django nos dois temas. Não comprimir manualmente CSS para esconder comportamento na cascata.
- Movimentações carregam listas completas em uma única requisição; paginação/índices podem ser necessários para conjuntos extensos, mas não houve `EXPLAIN ANALYZE`, amostra representativa nem medição. **Não alterar** consultas, índices ou ordenações além da relação de estorno auditada.
- `workspace_page` consulta permissões diversas vezes por perfil. Uma potencial otimização seria reduzir consultas redundantes, mas ACL varia por módulo, usuário, perfil e operação: **não criar cache sem testes de isolamento e contagem**.
- Sem PWA, cache offline financeiro, Telemetria externa, GA ou novos frameworks.

## Medição reprodutível futura

1. Em CI, execute manualmente `.github/workflows/ci.yml` (job `performance`), que usa banco exclusivamente `alece_test`. Não use Compose produtivo ou dados reais.
2. `tests/browser/test_performance_lab.py` utiliza a **mesma fixture Django/PostgreSQL** da suíte de regressão visual e gera cinco navegações em cada combinação de dez cenários de páginas e viewport 390/1280. Registra `responseStart` (aproximação ao tempo até primeiro byte, **não apenas processamento no servidor**), DOMContentLoaded, `load`, LCP e CLS observados pelo Chromium. **Não** possui interação consistente para atribuir INP: `interaction_sample_ms=null` é ausência de dado.
3. Salve JSON, JUnit, logs e captura em falhas do CI como artefatos internos. Não há envio a terceiros pela aplicação; GitHub Actions é infraestrutura escolhida pelo mantenedor para testes de dados **sintéticos**.
4. Faça uma execução com o código anterior e outra com o código novo **na mesma imagem, fixtures, CPU e rede**, salvando cada relatório fora do repositório. Use `python -m scripts.performance.compare_runs --before ... --after ... --output comparativo.html`. A comparação falha explicitamente se ambiente ou cenário divergirem e não inventa percentuais quando faltar dado.
5. Rode PostgreSQL `EXPLAIN (ANALYZE, BUFFERS)` **apenas em base sintética**, com o mesmo volume de dados. Avalie o número de consultas, tempo total, joins e acesso por índices; não gere logs com parâmetros financeiros de produção.
6. Qualquer regressão mensurável exige análise; não aplicar limites arbitrários em ambiente não calibrado. As fotografias das telas principais e fluxos de teclado continuam sob a suíte de regressão visual existente.

### Metodologia de Core Web Vitals

- Google/web.dev: LCP ≤2,5 s, INP ≤200 ms, CLS ≤0,1, **p75 de visitas reais**; é outra população estatística que a média/mediana de laboratório.
- Laboratório: execução fria e quente devem ser estudadas separadamente. O teste atual mede navegações sucessivas com cache do navegador preservado; os JSONs não são comparáveis a métricas de campo.
- INP requer sequência real de interações e percentil adequadamente amostrado. Não substituir INP por `load`, resposta HTTP ou simples `click()` sem medir atraso até pintura.

Fontes oficiais consultadas em 27/10/2026:
- https://web.dev/articles/vitals
- https://web.dev/articles/optimize-lcp
- https://docs.djangoproject.com/en/5.2/topics/db/optimization/

## Validação desta entrega

Sintaxe, contratos puros e integridade de ZIP podem ser verificados no ambiente de preparação. Ver `evidencias/validacao_local.log`, `evidencias/estaticos_antes.json`, `evidencias/estaticos_depois.json`, manifesto de hashes e documento de atualização. **Regressão Django/PostgreSQL e testes com participantes: não executados.**

## Testes locais concluídos e ressalvas

- 11 testes locais passaram, incluindo o contrato do comparador visual já existente e três testes novos da ferramenta de comparação de medidas; 1 warning informa ausência de `pytest-django`.
- Compilação Python, sintaxe dos JavaScripts existentes e carregamento YAML do workflow passaram.
- O observador de desempenho foi iniciado em Chromium com HTML **sintético** e confirmou presença de `PerformanceObserver`. A navegação em `data:` foi bloqueada pelo ambiente, então o smoke test foi repetido em `about:blank`. **Isso não constitui medição de uma página ALECE.**
- A primeira execução do contrato de isolamento visual falhou devido à comparação textual com `alece_test`; teste/guarda ajustados para permitir somente nomes explicitamente efêmeros `alece_test` ou `test_alece_test`, conservando as demais restrições. O reteste passou.
- Os contratos do Playwright real (10 cenários × 2 larguras × 5 repetições planejadas), a medição SQL, as principais tarefas com usuários e a regressão integrada aguardam execução em Django/PostgreSQL.
