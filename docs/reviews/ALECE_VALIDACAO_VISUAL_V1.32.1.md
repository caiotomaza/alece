# Validação visual v1.32.1 — 23/10/2026

## Ambiente e método

Referência preservada: `docs/prototype/ALECE_Prototipo_Visual_v1.32.1.html`, servida temporariamente em `127.0.0.1:8765`. Aplicação funcional: `http://127.0.0.1:8003/`, PostgreSQL isolado em `127.0.0.1:55433`, projeto Compose `alece-audit`. Os perfis **Visual completo** e **Visual vazio** contêm apenas dados sintéticos. O protótipo traz números de exemplo próprios; por isso, a comparação considera hierarquia e estilo, sem exigir igualdade de valores.

Edge automatizado por Playwright criou contextos separados com viewport exato de 320×640, 390×844, 768×1024 e 1440×900, DPR e escala 1, fontes carregadas e tema verificado antes de cada captura. Cada cenário produziu comparação lado a lado da primeira tela (`.png`) e da página inteira (`_full.png`). As imagens e `measurements.json` com dimensões, títulos, SHA-256 e erros ficam em `C:\Users\Caio Tomaz\backups\alece_visual_evidence_2026-10-23\final`. Permanecem fora do Git porque contêm amostras visíveis do protótipo. Foram capturados **80 cenários de página** (40 combinações em dois estados) e **48 cenários de modal**. Em todos os 128 cenários a aplicação abriu sem erro JavaScript nem rolagem horizontal global; todos os viewports tiveram dimensões efetivas iguais às solicitadas. As capturas são evidência de execução, **não** prova automática de equivalência.

## Legenda das diferenças e correções

| Código | Diferença observada na imagem final | Correção desta rodada |
| --- | --- | --- |
| D1 / C1 | Visão geral preenchida: a legenda do anel e o quadro do mês mantêm densidade e detalhamento distintos; valores de referência pertencem a dados diferentes. O vazio está próximo na composição. | Shell, SVG, hero, anel calculado com Decimal, seletor de perfis e estado vazio com Saldo. |
| D2 / C2 | Despesas: tabelas têm colunas e estados próprios do backend; o histórico ainda usa seleção de categoria em vez das abas de período do protótipo. | Cards, tabelas, ações +/lápis, filtro mensal, histórico de lotes confirmados e histórico no topo do estado vazio. |
| D3 / C3 | Investimentos: metas e edição da distribuição não reproduzem a tabela editável de pesos do protótipo; dados atuais e metas vêm dos serviços reais. | Quatro cards, resumo orçamentário, Reserva, sugestões com `NULL` preservado e formulário real em modal. |
| D4 / C4 | Movimentações: o modal + abre transferência entre contas, enquanto o protótipo oferece cadastro manual genérico; tabela e controles de importação diferem em detalhes. | Upload real CSV/OFX/PDF para prévia, KPIs do mês, histórico contábil e gráfico de lotes confirmados. |
| D5 / C5 | Configurações: a edição de perfis e permissões é encaminhada a telas autorizadas, em vez da grade editável diretamente no cartão. | Aparência, ferramentas, administração e acesso aos logs no mesmo shell e tokens. |
| D6 | Em 320/390 px, rótulos e espaçamento da navegação inferior têm pequenas diferenças; não houve corte funcional nem overflow global. | Barra móvel com cinco destinos, utilitários e seletor responsivo. |

## Matriz de páginas

Os caminhos abaixo são relativos ao diretório de evidências acima. Para cada par existem também os arquivos `_full.png`; os hashes de ambos constam em `measurements.json`. A coluna Diferença/correção aponta para a legenda. “Executado; paridade pendente” significa que a captura foi validada tecnicamente e a divergência visual indicada ainda existe.

| Destino | Viewport | Tema | Evidência preenchido · vazio | Diferença / correção | Resultado |
| --- | --- | --- | --- | --- | --- |
| Visão geral | 320×640 | Claro | `filled/overview/320x640_light.png` · `empty/overview/320x640_light.png` | D1+D6 / C1 | Executado; paridade pendente |
| Despesas | 320×640 | Claro | `filled/expenses/320x640_light.png` · `empty/expenses/320x640_light.png` | D2+D6 / C2 | Executado; paridade pendente |
| Investimentos | 320×640 | Claro | `filled/investments/320x640_light.png` · `empty/investments/320x640_light.png` | D3+D6 / C3 | Executado; paridade pendente |
| Movimentações | 320×640 | Claro | `filled/movements/320x640_light.png` · `empty/movements/320x640_light.png` | D4+D6 / C4 | Executado; paridade pendente |
| Configurações | 320×640 | Claro | `filled/settings/320x640_light.png` · `empty/settings/320x640_light.png` | D5+D6 / C5 | Executado; paridade pendente |
| Visão geral | 320×640 | Escuro | `filled/overview/320x640_dark.png` · `empty/overview/320x640_dark.png` | D1+D6 / C1 | Executado; paridade pendente |
| Despesas | 320×640 | Escuro | `filled/expenses/320x640_dark.png` · `empty/expenses/320x640_dark.png` | D2+D6 / C2 | Executado; paridade pendente |
| Investimentos | 320×640 | Escuro | `filled/investments/320x640_dark.png` · `empty/investments/320x640_dark.png` | D3+D6 / C3 | Executado; paridade pendente |
| Movimentações | 320×640 | Escuro | `filled/movements/320x640_dark.png` · `empty/movements/320x640_dark.png` | D4+D6 / C4 | Executado; paridade pendente |
| Configurações | 320×640 | Escuro | `filled/settings/320x640_dark.png` · `empty/settings/320x640_dark.png` | D5+D6 / C5 | Executado; paridade pendente |
| Visão geral | 390×844 | Claro | `filled/overview/390x844_light.png` · `empty/overview/390x844_light.png` | D1+D6 / C1 | Executado; paridade pendente |
| Despesas | 390×844 | Claro | `filled/expenses/390x844_light.png` · `empty/expenses/390x844_light.png` | D2+D6 / C2 | Executado; paridade pendente |
| Investimentos | 390×844 | Claro | `filled/investments/390x844_light.png` · `empty/investments/390x844_light.png` | D3+D6 / C3 | Executado; paridade pendente |
| Movimentações | 390×844 | Claro | `filled/movements/390x844_light.png` · `empty/movements/390x844_light.png` | D4+D6 / C4 | Executado; paridade pendente |
| Configurações | 390×844 | Claro | `filled/settings/390x844_light.png` · `empty/settings/390x844_light.png` | D5+D6 / C5 | Executado; paridade pendente |
| Visão geral | 390×844 | Escuro | `filled/overview/390x844_dark.png` · `empty/overview/390x844_dark.png` | D1+D6 / C1 | Executado; paridade pendente |
| Despesas | 390×844 | Escuro | `filled/expenses/390x844_dark.png` · `empty/expenses/390x844_dark.png` | D2+D6 / C2 | Executado; paridade pendente |
| Investimentos | 390×844 | Escuro | `filled/investments/390x844_dark.png` · `empty/investments/390x844_dark.png` | D3+D6 / C3 | Executado; paridade pendente |
| Movimentações | 390×844 | Escuro | `filled/movements/390x844_dark.png` · `empty/movements/390x844_dark.png` | D4+D6 / C4 | Executado; paridade pendente |
| Configurações | 390×844 | Escuro | `filled/settings/390x844_dark.png` · `empty/settings/390x844_dark.png` | D5+D6 / C5 | Executado; paridade pendente |
| Visão geral | 768×1024 | Claro | `filled/overview/768x1024_light.png` · `empty/overview/768x1024_light.png` | D1 / C1 | Executado; paridade pendente |
| Despesas | 768×1024 | Claro | `filled/expenses/768x1024_light.png` · `empty/expenses/768x1024_light.png` | D2 / C2 | Executado; paridade pendente |
| Investimentos | 768×1024 | Claro | `filled/investments/768x1024_light.png` · `empty/investments/768x1024_light.png` | D3 / C3 | Executado; paridade pendente |
| Movimentações | 768×1024 | Claro | `filled/movements/768x1024_light.png` · `empty/movements/768x1024_light.png` | D4 / C4 | Executado; paridade pendente |
| Configurações | 768×1024 | Claro | `filled/settings/768x1024_light.png` · `empty/settings/768x1024_light.png` | D5 / C5 | Executado; paridade pendente |
| Visão geral | 768×1024 | Escuro | `filled/overview/768x1024_dark.png` · `empty/overview/768x1024_dark.png` | D1 / C1 | Executado; paridade pendente |
| Despesas | 768×1024 | Escuro | `filled/expenses/768x1024_dark.png` · `empty/expenses/768x1024_dark.png` | D2 / C2 | Executado; paridade pendente |
| Investimentos | 768×1024 | Escuro | `filled/investments/768x1024_dark.png` · `empty/investments/768x1024_dark.png` | D3 / C3 | Executado; paridade pendente |
| Movimentações | 768×1024 | Escuro | `filled/movements/768x1024_dark.png` · `empty/movements/768x1024_dark.png` | D4 / C4 | Executado; paridade pendente |
| Configurações | 768×1024 | Escuro | `filled/settings/768x1024_dark.png` · `empty/settings/768x1024_dark.png` | D5 / C5 | Executado; paridade pendente |
| Visão geral | 1440×900 | Claro | `filled/overview/1440x900_light.png` · `empty/overview/1440x900_light.png` | D1 / C1 | Executado; paridade pendente |
| Despesas | 1440×900 | Claro | `filled/expenses/1440x900_light.png` · `empty/expenses/1440x900_light.png` | D2 / C2 | Executado; paridade pendente |
| Investimentos | 1440×900 | Claro | `filled/investments/1440x900_light.png` · `empty/investments/1440x900_light.png` | D3 / C3 | Executado; paridade pendente |
| Movimentações | 1440×900 | Claro | `filled/movements/1440x900_light.png` · `empty/movements/1440x900_light.png` | D4 / C4 | Executado; paridade pendente |
| Configurações | 1440×900 | Claro | `filled/settings/1440x900_light.png` · `empty/settings/1440x900_light.png` | D5 / C5 | Executado; paridade pendente |
| Visão geral | 1440×900 | Escuro | `filled/overview/1440x900_dark.png` · `empty/overview/1440x900_dark.png` | D1 / C1 | Executado; paridade pendente |
| Despesas | 1440×900 | Escuro | `filled/expenses/1440x900_dark.png` · `empty/expenses/1440x900_dark.png` | D2 / C2 | Executado; paridade pendente |
| Investimentos | 1440×900 | Escuro | `filled/investments/1440x900_dark.png` · `empty/investments/1440x900_dark.png` | D3 / C3 | Executado; paridade pendente |
| Movimentações | 1440×900 | Escuro | `filled/movements/1440x900_dark.png` · `empty/movements/1440x900_dark.png` | D4 / C4 | Executado; paridade pendente |
| Configurações | 1440×900 | Escuro | `filled/settings/1440x900_dark.png` · `empty/settings/1440x900_dark.png` | D5 / C5 | Executado; paridade pendente |

## Modais e interação

`modals/measurements.json` documenta 6 interações × 4 resoluções × 2 temas = **48 comparações** lado a lado: renda, conta, despesa previsível, despesa imprevisível, investimento e movimentação. Cada registro contém o retângulo do diálogo e o SHA-256 da captura. Todos permaneceram dentro do viewport, sem erro JavaScript ou overflow global. O modal financeiro agora abre sobre a página de origem, inclui cabeçalho/fechamento e mantém ações no rodapé; o formulário enviado continua sendo o do Django. Persistem campos e textos diferentes do protótipo, sobretudo no cadastro manual de movimentação.

A jornada `scripts/e2e_visual_audit.py` abriu e fechou modais em oito combinações, alternou tema, selecionou perfil e mês, persistiu uma despesa sintética no PostgreSQL, confirmou que seu cadastro não criou lote no ledger, verificou acesso somente leitura, revogação na requisição seguinte e Logs do Sistema permitidos ao administrador e negados ao usuário Comum. Capturas dessa jornada ficam no diretório temporário `alece-e2e`.

## Aceite e limites

**A equivalência visual substancial continua pendente**, principalmente D3–D5. As tabelas e gráficos abaixo da primeira tela foram capturados integralmente, mas não passaram por um roteiro de correção visual de cada célula em cada estado. A CI remota e o navegador no ZimaOS não foram executados. Não há declaração de homologação final nem autorização para dados reais.
