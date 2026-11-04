# Relatório de validação — ALECE Design System 1.0

**Data:** 2026-10-27 · **Ambiente de verificação:** Linux contêiner de auditoria, Chromium headless, Python 3.13, Playwright; sem aplicação Django autenticada e sem PostgreSQL.

## Procedimento de evidência

- **Antes**: prévia técnica criada com marcação equivalente aos componentes ALECE, usando **CSS original do ZIP de entrada**, para temas claro e escuro e viewports desktop 1280 × 900 / mobile 390 × 844.
- **Depois**: a **mesma prévia** com CSS consolidado. Foi usada renderização real do Chromium por `page.set_content` com folhas locais embutidas; navegação por arquivo e localhost é bloqueada pela política deste contêiner.
- Capturas disponíveis em `docs/design-system/evidencias/antes_{light,dark}_{desktop,mobile}.png` e `depois_*`, com métricas em `antes_medidas.json` e `depois_medidas.json`.
- Os exemplos possuem **somente dados fictícios**. Não são capturas de telas reais logadas, nem testam fluxos financeiros, banco ou conteúdo gerado por Django.

## Constatações da amostra

| Verificação | Antes | Depois |
|---|---|---|
| Altura do botão padrão, desktop | 42 px | 44 px |
| Altura do botão padrão, mobile | 41 px | 44 px |
| Altura de input/select da amostra | 46 px | 44 px |
| Checkbox/radio | geometrias concorrentes | 20 px no catálogo |
| Select | imagem de fundo com regras concorrentes | caret único sobre superfície lisa |
| Ação destrutiva | verde como primária em parte dos componentes | cor destrutiva semântica |
| Tabela | sem gutter comum no wrapper da amostra | espaçamento lateral uniforme |
| Mensagens de status | estilos variáveis | variantes success/error com borda |
| Overflow horizontal da página | não observado na prévia | não observado na prévia; a tabela mantém rolagem local |

## Limitações / riscos residuais

1. **Pendente** testar rotas e telas autenticadas (dashboard, despesas, investimentos, movimentos, configurações, permissões, importação, relatórios, modais e recuperação) com Django/servidor funcional e dados não produtivos. Nenhuma regressão funcional integrada foi aprovada aqui.
2. **Pendente** revisar capturas reais antes/depois em Firefox, Chromium e Android/WebView com o sistema em funcionamento. Dropdowns nativos variam conforme plataforma.
3. **Pendente** auditoria manual por teclado e leitores de tela, contraste medido em estados efetivos, zoom 200%/400%, idiomas e cenários de dados extensos. Sem alegação de WCAG 2.2 AA.
4. Seletores históricos especializados, blocos inline de layouts de autenticação e `!important` não relacionados aos campos continuam presentes. A remoção completa demandaria mudança de risco alto e deve ser segmentada.
5. A página de erro HTTP mantém CSS independente para oferecer fallback durante falhas da própria aplicação.

## Execução de testes

Resultados reais encontram-se em `docs/design-system/TESTES_E_REGISTRO.md`, gerado durante a validação, e no log da intervenção. Como instalar dependências não faz parte do escopo, testes Django não serão apresentados como executados quando ausentes.
