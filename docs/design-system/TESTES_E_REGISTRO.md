# Testes e registro de execução — 27/10/2026

## Resultado obtido

| Categoria | Resultado observado |
|---|---|
| `pytest tests/design_system/` com pré-verificação de ambiente isolado (`ALECE_TEST_ISOLATED=1`, `ALECE_DB_NAME=test_designsystem`, `ALECE_DB_HOST=localhost`) | **10 testes aprovados** (6 contratos CSS/HTML + 4 visuais Chromium), 1 warning da suíte |
| `node --check src/view/static/finance/alece.js` | Aprovado (sintaxe JavaScript; não teste funcional) |
| `python -m compileall -q tests/design_system` | Aprovado (compilação de testes; não teste funcional) |
| CSS `tinycss2.parse_stylesheet` | Sem erros de gramática de nível superior nos 4 CSS testados |
| Chromium (renderização de amostra isolada) | 4 capturas antes + 4 depois, desktop/mobile e light/dark; geometria e caret testados |
| Controle de foco por teclado nos campos da amostra | Aprovado após correção; a primeira rodada teve 4 falhas por `outline: none` legado |
| Alterações de backend/JS/migrations | Nenhuma; `alece.js` verificado sintaticamente |
| Regressão Django integrada, PostgreSQL, testes E2E reais | **Não executados**: Django / pytest-django / PostgreSQL indisponíveis neste ambiente de auditoria |
| Capturas de telas reais autenticadas e inspeção manual WCAG 2.2 AA | **Pendentes**; as capturas são só do catálogo estático com dados fictícios |

O projeto se protege contra testes involuntários no banco: uma primeira invocação de pytest sem as variáveis de isolamento foi **bloqueada corretamente** pelo guard existente. As variáveis de teste fornecidas não apontam para um banco, pois os novos testes são autocontidos e não acessam Django nem rede. O log de auditoria foi preservado e incluído como `docs/design-system/LOG_EXECUCAO.log`.

## Identidade e preservação

As cores de fundo dos temas claro/escuro, mensuradas no Chromium, coincidem entre a amostra antes e depois. A imagem da seta do select foi verificada como URL SVG válida no estilo computado. Os botões e controles simples da amostra passaram a ter altura 44 px nos dois tamanhos de viewport. `.env` e `.env.example` foram preservados **byte a byte** do ZIP de origem, sem exibição de segredos. Nenhuma migration foi criada ou alterada.

A suíte visual comprova o comportamento **do catálogo de componentes**, não todas as telas do ALECE. Antes de liberar em produção, realizar homologação do sistema Django completo e revisar os riscos residuais citados no relatório visual.
