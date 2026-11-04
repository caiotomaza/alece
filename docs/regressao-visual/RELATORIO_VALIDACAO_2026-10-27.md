# ALECE — Relatório de regressão visual | 2026-10-27

## Origem e integridade

Base única: `ALECE_COMPLETO_ACESSIBILIDADE_WCAG_2_2_2026-10-27.zip`,
SHA-256 conferido com o `.zip.sha256` recebido. Backup integral de intervenção
copiado em `$HOME/backups/` e SHA-256 verificado antes de qualquer mudança.
Registros da intervenção em `$HOME/logs/YYYY-MM-DD_HH-MM-SS.log` e cópia
sanitizada neste diretório.

**Escopo alterado:** testes E2E/Playwright, comparador PNG, documentação,
marca pytest e workflow CI. Não houve alterações em Python/CSS/JS da aplicação,
modelos, migrations, rotas, permissões, composição dos serviços e `.env`.

## Resultado factual da execução local

| Verificação | Resultado | Evidência |
|---|---|---|
| ZIP da versão de entrada e SHA-256 | Aprovado | registro da intervenção |
| Integridade estrutural ZIP origem | Aprovado | `unzip -t` |
| Teste unitário de falta de baseline | Aprovado (reprova como esperado) | unittest |
| Teste de diferença visual relevante | Aprovado (gera diff) | unittest |
| Limite de diferença e tamanho | Aprovado | unittest |
| Guardas CI sem aprovação automática | Aprovado | unittest |
| Testes locais do comparador e CI | **8 aprovados, 0 falhas** | `evidencias/validacao_local.log` |
| Compilação Python dos arquivos novos | Aprovado | `compileall` |
| Sintaxe YAML CI | Aprovado | PyYAML `safe_load` |
| Django com PostgreSQL real e Playwright | **NÃO TESTADO** | Django/psycopg/pytest-playwright não disponíveis |
| axe-core integrado na aplicação real | **NÃO TESTADO** | pacote e browser da CI não executados localmente |
| HTML/JUnit real e screenshots de telas Django | **NÃO GERADOS** | exigem execução do job visual da CI |
| Referências visuais aprovadas | **0 — PENDENTE DE REVISÃO** | pasta de referências contém somente README |

Nenhuma captura de catálogo isolado das etapas anteriores foi reutilizada como
baseline: seria falsificar evidência de renderização da aplicação real.

## Cobertura planejada no CI (não confundir com teste executado)

24 cenários de tela/estado × 2 temas × 5 viewports (320, 390, 768, 1280, 1920)
= **240 combinações planejadas**, além de testes isolados de acesso e teclado.
São cenários cadastrados, não aprovações de teste. O job usa PostgreSQL local
à rede efêmera do runner, usuário sintético e autenticação pelo backend Django.

| Requisito | Cenários | Resultado local |
|---|---|---|
| Visão geral com e sem lançamentos | overview_empty, overview_filled | não testado |
| Despesas vazias/preenchidas | expenses_empty, expenses_filled | não testado |
| Investimentos vazios/preenchidos | investments_empty, investments_filled | não testado |
| Movimentações e importação | movements_filled, import_upload | não testado |
| Configurações comuns | settings_common | não testado |
| Gerência admin | admin_users, admin_profiles, admin_ai | não testado |
| Formulários | profile_edit, expense_edit | não testado |
| Integração IA | admin_ai (sem chamada externa) | não testado |
| Logs e relatórios | logs, reports, reports_financial | não testado |
| Modal e validação | modal_invalid; test_keyboard_modal_open_escape_and_focus_restore | não testado |
| Menus e filtros | dropdown_open, filter_focus, button_hover | não testado |
| Feedback | message_success, message_error, forbidden | não testado |
| Acesso administrativo de conta comum | test_visual_permissions_real_http | não testado |

## Problemas conhecidos, por gravidade

1. **P1 — Baseline ainda não homologada:** nenhum screenshot da aplicação real
   pôde ser revisado. O modo compare deve reprovar até aprovação formal.
2. **P1 — Cobertura HTTP real não executada nesta entrega:** nenhuma das
   240 combinações recebeu evidência de execução; selectors e URLs dependem
   da CI e podem revelar regressões preexistentes que exigirão correção.
3. **P1 — axe-core não executado:** as avaliações WCAG automatizáveis não
   foram produzidas no ambiente de autoria. Falha na instalação do scanner
   deve reprovar explicitamente o job, não ser ignorada.
4. **P2 — Renderização dependente do sistema:** a imagem da CI está fixada
   por tag Playwright/Ubuntu, mas ainda precisa de digest imutável e revisão
   de fontes entre execuções para resultados mais determinísticos.
5. **P2 — Data e elementos dinâmicos:** células de horário de logs são
   mascaradas nos screenshots; validade e conteúdo reais devem continuar
   cobertos por testes funcionais Django. Falsos positivos visuais devem ser
   investigados, sem ampliar tolerâncias para escondê-los.
6. **P2 — Dependência npm:** axe-core tem versão fixa, porém instalação sem
   lockfile de integridade; travar tarball no processo de hardening do CI.
7. **P2 — Janelas e estados não exaustivos:** matrizes de seleção financeira,
   dropdowns do navegador e estados de carregamento transientes requerem
   revisão e refinamento após executar o primeiro ciclo real.
8. **P3 — Não substitui avaliação manual:** leitores de tela, usabilidade,
   zoom, texto em alta ampliação, idioma e percepção de contraste exigem
   inspeção humana com os critérios aplicáveis WCAG 2.2 AA.

## Critério de aceite e veredito

Implementado: mecanismo que reprova diferença/ausência de baseline com
identificação da tela e evidência, além de pipeline com captura e análise axe.
**Ainda não demonstrado em aplicação real:** falha automática por regressão
visual no CI, geração completa de screenshots reais, acessibilidade do HTML
autenticado e estabilidade/adequação das baselines. Não promover a suíte a
requisito de release aprovado antes de capturar, revisar e versionar PNGs da
aplicação real e concluir uma execução em modo compare com zero falhas.

## Fontes técnicas consultadas

- Playwright Python: https://playwright.dev/python/docs/docker
- Playwright Python / pytest: https://playwright.dev/python/docs/test-runners
- Playwright snapshots/review: https://playwright.dev/docs/test-snapshots
- Playwright acessibilidade (axe): https://playwright.dev/docs/accessibility-testing
- Playwright testes com artefatos: https://playwright.dev/docs/test-reporters
- Django testes e bancos: https://docs.djangoproject.com/en/5.2/topics/testing/overview/
- pytest-django isolamento: https://pytest-django.readthedocs.io/en/latest/database.html
