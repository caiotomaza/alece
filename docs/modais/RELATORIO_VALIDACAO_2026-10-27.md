# ALECE — Relatório de validação: formulários, modais e feedback

**Data:** 27/10/2026. **Base:** ZIP integral Design System 1.0 (SHA-256 conferido). **Status:** testes de componente aprovados; homologação integrada **pendente**.

## Resultados executados

| Verificação | Resultado real | Evidência |
|---|---|---|
| Playwright/Chromium com respostas simuladas | 20 casos aprovados | `evidencias/pytest_modais_e_design_system.xml` |
| Contratos do Design System anterior | 10 casos aprovados | mesmo XML |
| Total | **30 passaram, 0 falharam**, 1 aviso pytest (`pytest-django` indisponível) | `evidencias/testes_frontend.log` |
| Sintaxe JavaScript | `node --check` de ambos os JS: aprovado | log |
| Código Python | `python -m compileall -q src/controller`: aprovado (apenas sintaxe/bytecode) | log |
| Django/PostgreSQL HTTP, transações, migrations | **Não executados** (Django, pytest-django e PostgreSQL ausentes) | log |
| Renderização comparativa | duas capturas Chromium de **componente simulado**, sem servidor real | `evidencias/componente_simulado_*.png` |
| Telas autenticadas com dados financeiros | **Não executadas** | pendência |

## Comportamentos verificados com Chromium

- Apertar Escape e clicar fora fecham (sem alterações) ou perguntam antes (com alterações).
- Alterações descartadas não produzem POST; “Continuar editando” preserva o formulário.
- Com único formulário não sensível alterado, “Salvar” envia apenas seu próprio `requestSubmit()`; respostas HTTP 403, 409 e 500 mantêm o modal e apresentam a mensagem adequada. Não houve falsa indicação de sucesso.
- Em formulários múltiplos alterados e formulários sensíveis, o botão de salvar em massa não é oferecido; a interface orienta salvar cada seção e não envia requisições ao fechar. Desvio deliberado da tríade literal de ações para respeitar o requisito superior de evitar gravações indevidas; requer avaliação de produto.
- Confirmação destrutiva deixa a ação mais segura em foco; cancelar não encaminha o formulário, confirmar envia exatamente uma tentativa.
- Foco retorna ao gatilho do modal, Tab não escapa do diálogo, o fundo permanece modal/inert, e o bloqueio de rolagem é retirado ao fechar.
- Campos com erro recebem `aria-invalid` e associação do elemento de erro.
- Geometria verificada nas viewports de **390×760** e **1280×820**, em **claro e escuro**.
- Percurso comum de formulário representativo de usuário, perfil, despesa, investimento e IA foi executado com conteúdo simulado; **não são testes das respectivas views Django**.

## Falhas encontradas e resolvidas durante testes

1. Testes iniciais foram bloqueados pela política de navegação do Chromium (`ERR_BLOCKED_BY_ADMINISTRATOR`). Fixture alterada para HTML sem rede via `page.set_content` e `fetch` simulado; limitação documentada.
2. O teste de foco constatou saída transitória para o `<body>` no ciclo de Tab do Chromium headless. Correção centralizada do wrap Tab/Shift+Tab; depois todos passaram.
3. `pytest` inicialmente recusou execução sem variáveis de isolamento. As flags de test DB/host foram definidas apenas para a execução local. Nenhum banco real foi acessado.

## Aceite ainda não demonstrado

As operações reais de criar, editar, cancelar, excluir e erro de validação em usuários, perfis, despesas, investimentos e integrações de IA exigem Django 5.2.18, PostgreSQL isolado, credenciais de teste e navegador conectado ao serviço. Além disso, homologar navegação sem JS com servidor, mobile real, teclado/leitor de tela, ações de importação e idempotência/atomicidade financeira.

**Proibição de inferência:** os testes Playwright de fragmentos HTML não certificam autorização, persistência, CSRF, transações, LGPD ou WCAG 2.2 AA. Não foi feita nenhuma alteração na aplicação/banco de produção.
