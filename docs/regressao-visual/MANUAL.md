# ALECE — regressão visual real (Playwright + axe-core)

## O que é e o que não é

A suíte em `tests/browser/test_visual_regression.py` usa HTTP real no
`live_server` do Django, PostgreSQL de teste efêmero, autenticação do próprio
Django e dados financeiros fictícios. Não é um mock de HTML nem faz requests
a provedores de IA. A pipeline funcional original é preservada.

**Não existem baselines aprovadas nesta entrega**: o ambiente de autoria não
tinha Django/PostgreSQL nem acesso ao serviço CI. O primeiro job em modo
`compare` deverá falhar fechado por baseline ausente até que sejam capturadas,
revisadas e adicionadas ao repositório as imagens reais. Não declarar a suíte
visual homologada antes desse processo.

## Versões e determinismo

- CI: `ubuntu-24.04`, container `mcr.microsoft.com/playwright/python:v1.64.1-noble`
  (mesma versão `playwright==1.64.1` de `browser.in`), Chromium embutido;
  recomenda-se congelar digest da imagem após aprovação interna.
- PostgreSQL 16 Bookworm **separado**, DB/user `alece_test`; sem montar volumes
  do ALECE ou acessar banco de produção.
- Python dependencies: `development.lock --require-hashes`; Pillow 12.3.0;
  pytest-html 4.2.0; axe-core 4.14.0. Incluir lock/npm integrity em hardening
  posterior para defesa de supply chain.
- Timezone America/Fortaleza; locale C.UTF-8; dispositivo emulação Chromium;
  viewport 320x720, 390x844, 768x1024, 1280x800, 1920x1080,
  temas claro e escuro; `prefers-reduced-motion: reduce`; animações desativadas.
- Campos financeiros fictícios e datas fixas (outubro/2026), filtro de mês
  quando disponível. Datas de criação dos perfis estão fixas e as células
  temporais dos logs são mascaradas para comparação de geometria; o conteúdo
  dos logs continua sendo validado separadamente.

## Captura inicial com aprovação humana obrigatória

1. Em GitHub Actions > CI > Run workflow, escolha `visual_mode=capture`.
   O modo captura **NUNCA grava** em `tests/browser/visual_baselines/`.
2. Baixe o artifact `alece-visual-capture-evidence` com os candidatos
   `test-results/visual/candidates/*.png` e relatório HTML/JUnit/axe.
3. Compare uma a uma com o design esperado e revise contraste, disposição,
   ocultação, foco, dados fictícios e responsividade. Corrija bugs antes de
   aprovar. Registre revisor, data, PR e justificativa da mudança visual.
4. Adicione somente os PNGs **aprovados** à pasta
   `tests/browser/visual_baselines/` e abra PR dedicado.
5. Execute novamente a CI em `visual_mode=compare` (default). A ausência de
   baseline, a divergência ou falhas de axe/overflow reprovarão a pipeline.

**Nunca** executar modo `capture` para "passar" CI nem copiar automaticamente
capturas à baseline. Nada de `--update-snapshots` em automações.

## Executar localmente (somente banco/test server descartáveis)

É obrigatória uma instância de PostgreSQL EFÊMERA com os parâmetros
`ALECE_TEST_ISOLATED=1`, `ALECE_DB_NAME=alece_test`, `ALECE_DB_HOST=127.0.0.1`
ou `postgres`, `DJANGO_SETTINGS_MODULE=config.test_settings`. Não use `.env`
produtivo. O preflight falha se o alvo não for reconhecido.

Executar no mesmo container Chromium da CI com dependências e axe instalados:

```bash
ALECE_VISUAL_MODE=compare pytest -q tests/browser/test_visual_regression.py \
  -m visual --browser chromium --output=test-results/visual/runner \
  --junitxml=test-results/visual/junit.xml \
  --html=test-results/visual/report.html --self-contained-html
```

Alterações pontuais: `ALECE_VISUAL_MODE=capture` apenas para gerar candidatos.

## Critérios de falha e evidências

- Arquivo de baseline ausente: falha, não cria referência.
- Diferença superior a **0,10% dos pixels** (tolerância de 12 níveis de canal
  RGB por pixel): falha; salva imagem atual, imagem diff e motivo textual.
- Captura com dimensões diferentes: falha, salva imagem atual e motivo.
- Página diferente de HTTP 200, controle obrigatório ausente, menu/modal
  sem estado esperado, overflow horizontal indevido: falha e screenshot de
  falha no runner Playwright.
- Qualquer violação WCAG A/AA detectada pelo axe-core: falha, relatório JSON
  específico com elementos e identificação do cenário. `incomplete` é mantido
  para revisão humana; scanners não são certificação WCAG.
- A pipeline sempre exporta `test-results/visual/` com PNGs, diffs, JSON axe,
  `report.html` e `junit.xml`, mesmo em falha.

## Estados cobertos

`overview_empty`, `overview_filled`, `expenses_empty`, `expenses_filled`,
`investments_empty`, `investments_filled`, `movements_filled`, `import_upload`,
`settings_common`, `admin_users`, `admin_profiles`, `admin_ai`, `profile_edit`,
`expense_edit`, `logs`, `reports`, `dropdown_open`, `modal_invalid`,
`message_success`, `message_error`, `forbidden`, `reports_financial`,
`filter_focus`, `button_hover`.

O dashboard em branco não deve receber saldo inventado. A administração exige
permissão efetiva de backend. Os dados são criados a cada teste e descartados.

## Leitura e triagem

- P0: vazamento de dados reais, alterações em produção, falha de isolamento.
- P1: controle inacessível, tela inacessível, sobreposição crítica, contraste
  crítico, ação financeira impossível.
- P2: mudanças geométricas e de componentes fora do padrão.
- P3: pequena variação de rasterização que exija justificativa e aprovação.

Os resultados dependem de font/renderização. Não aumentar limiares para ocultar
falhas; rever primeiro diferenças ambientais e atualizar baselines só via PR.
Verificar manualmente leitores de tela e teclado nas jornadas críticas.

## Rollback

As mudanças são somente testes, documentação e CI. Em caso de incidente,
reverter o commit da suíte/CI e restaurar a versão anterior do projeto usando
o backup SHA-256 validado. Não houve alteração de modelos, migrações, `.env`,
volumes ou códigos da aplicação.
