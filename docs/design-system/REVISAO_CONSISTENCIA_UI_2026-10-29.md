# ALECE — revisão de consistência visual (29/10/2026)

## Escopo e decisão

Base: `ALECE_COMPLETO_MODAL_RENDA_SEM_LINHAS_2026-10-29.zip`. Foram inventariados os templates em `src/view/templates`, os CSS em `src/view/static` e os módulos JavaScript próprios. Foram consultados `AGENTS.md`, documentação de Design System, normas de acessibilidade e contratos de modais e do modal de renda.

A estratégia é consolidar a apresentação **sem mudar** Python, Django, rotas, seletores DOM de negócio, persistência, migrations, pagamentos ou os dados financeiros. O visual continua sóbrio, com verde ALECE, superfícies sólidas, bordas suaves, raios e espaçamentos compartilhados, nos temas Claro/Escuro. Indicadores de foco e contraste de controles não devem desaparecer em nome da estética. Gráficos e áreas de destaque podem manter exceções decorativas documentadas.

## Alterações efetivas

- `src/view/static/finance/alece_auth.css` centraliza os estilos das três páginas standalone de autenticação e recuperação. Removidas as cópias de CSS inline dos templates `auth/login.html`, `auth/recovery_request.html` e `auth/recovery_use.html`, mantendo campos, nomes, métodos de formulário, tokens CSRF e fluxos existentes.
- `src/view/static/finance/alece.css` deixa de usar gradientes em filtros de integração de IA, no hover de atalhos e no destaque da página institucional. Permanecem exceções de gráfico e destaque originalmente previstas no Design System.
- `src/view/static/finance/alece_components.css`, `alece_modals.css` e `src/view/static/core/setup.css` aproximam os cartões, controles e diálogos dos raios e superfícies do catálogo, com sombras contidas e foco preservado.
- `src/view/templates/core/system_logs_list.html` e `system_log_detail.html` alinham raios e superfícies dos painéis e controles; `error_page.html` mantém CSS independente para resiliência, porém com a mesma paleta Claro/Escuro.
- Três asserções nos roteiros de prévia do modal de renda foram corrigidas para verificar **o input** (elemento com raio e foco visível), e não o wrapper `.alece-income-money`. Os testes anteriores falhavam na base original por essa confusão, sem indicar necessariamente falha de aplicação.
- `tests/design_system/test_auth_consistency.py` protege carregamento das folhas e uso de tokens em autenticação. A verificação de configuração inicial em `tests/operations/test_repository_structure.py` passa a reconhecer o token semântico novo além do alias legado.

## Evidências e limites

- Sintaxe CSS: parse de todas as 9 folhas próprias com `tinycss2`, sem erros de gramática.
- Sintaxe JavaScript: `node --check` em todos os arquivos JS da aplicação e biblioteca local, sem erro.
- Testes de contratos visuais, acessibilidade estrutural e modal de renda: **45 testes aprovados** em execução com pré-condições de ambiente isolado, sem conexão com banco real.
- Chromium com conteúdo sintético: **30 combinações** (3 telas de autenticação × 2 temas × 5 larguras, de 320 a 1920 CSS px) com geometria de cards/inputs/botões e sem overflow horizontal; **10 cenários** de modal de renda do roteiro redesenhado, **2 cenários** do roteiro de interações, **10 cenários** de moeda/foco e **10 combinações** do painel de Visão geral. Capturas dos scripts foram geradas numa cópia temporária do projeto, sem alterar evidências históricas no pacote entregue.
- **Não executados nesta revisão:** login e navegação Django autenticados, POST real, banco PostgreSQL efêmero, suíte pytest de integração completa, auditoria assistiva/manual WCAG 2.2 AA, validação do contraste de cada estado dinâmico ou aprovação de baselines visuais reais. Sem essas verificações, não é correto declarar todas as telas homologadas, WCAG certificado ou ausência integral de regressões.

## Aceite de implantação

Em ambiente **isolado e com dados fictícios**, seguir `docs/regressao-visual/MANUAL.md` e `docs/qualidade/DEFINITION_OF_DONE.md`. Verificar páginas públicas, cinco destinos, telas administrativas, relatórios, modais e mensagens em 320, 390, 768, 1280 e 1920 px nos dois temas. Revalidar formulários sem JS, foco/teclado, operações e permissões antes de publicar. Em instalação existente, preservar `.env`, banco e volumes e produzir backup verificado antes de qualquer rebuild. Nenhuma instalação existente foi alterada por esta revisão.
