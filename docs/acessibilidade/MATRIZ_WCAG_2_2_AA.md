# Matriz WCAG 2.2 — ALECE (níveis A e AA)

**Data:** 2026-10-27. **Escopo:** ZIP atual recebido; inspeção de código e prévia offline com Playwright/Chromium, não aplicação Django autenticada.

**Status de cada critério:** Aprovado = verificado em toda a aplicação e cenários aplicáveis; Reprovado = falha confirmada; Não aplicável = não há conteúdo exigindo o critério no material inspecionado; Não testado = ausência de evidência suficiente. Nenhum critério de conformidade do produto foi marcado como Aprovado apenas por scanner, código-fonte ou prévia.

| Critério | Requisito | Status | Evidência/limite |
|---|---|---|---|
| 1.1.1 | Conteúdo não textual | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 1.2.1 | Somente áudio e somente vídeo (pré-gravado) | Não aplicável* | Nenhum áudio/vídeo detectado nos templates do ZIP; reavaliar se houver novas mídias. |
| 1.2.2 | Legendas (pré-gravadas) | Não aplicável* | Nenhum áudio/vídeo detectado nos templates do ZIP; reavaliar se houver novas mídias. |
| 1.2.3 | Audiodescrição ou mídia alternativa (pré-gravada) | Não aplicável* | Nenhum áudio/vídeo detectado nos templates do ZIP; reavaliar se houver novas mídias. |
| 1.2.4 | Legendas (ao vivo) | Não aplicável* | Nenhum áudio/vídeo detectado nos templates do ZIP; reavaliar se houver novas mídias. |
| 1.2.5 | Audiodescrição (pré-gravada) | Não aplicável* | Nenhum áudio/vídeo detectado nos templates do ZIP; reavaliar se houver novas mídias. |
| 1.3.1 | Informações e relações | Não testado | 110 th com scope adicionados; associações complexas e formulários não revisados integralmente. |
| 1.3.2 | Sequência significativa | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 1.3.3 | Características sensoriais | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 1.3.4 | Orientação | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 1.3.5 | Identificar a finalidade da entrada | Não testado | Autocomplete de entrada preservado; finalidade de todos os campos não inspecionada manualmente. |
| 1.4.1 | Uso de cores | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 1.4.2 | Controle de áudio | Não aplicável* | Nenhum áudio/vídeo detectado nos templates do ZIP; reavaliar se houver novas mídias. |
| 1.4.3 | Contraste (mínimo) | Não testado | Tokens comparados por luminância; contrastes de todos os conteúdos e estados não medidos. |
| 1.4.4 | Redimensionar texto | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 1.4.5 | Imagens de texto | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 1.4.10 | Reflow | Não testado | Chromium estático em 320/390/768/1280/1920px sem overflow documental; telas Django não ensaiadas. |
| 1.4.11 | Contraste não textual | Não testado | Bordas dos campos reforçadas acima de 3:1 na prévia; outros indicadores não medidos. |
| 1.4.12 | Espaçamento de texto | Não testado | Espaçamento de texto customizado não validado em páginas reais. |
| 1.4.13 | Conteúdo em hover/foco | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 2.1.1 | Teclado | Não testado | Prévia com skip link, formulário e details operados por teclado; jornadas reais pendentes. |
| 2.1.2 | Sem armadilha de teclado | Não testado | Regressão de modais simulados aprovada; foco em telas reais não testado. |
| 2.1.4 | Atalhos de teclado por caractere | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 2.2.1 | Tempo ajustável | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 2.2.2 | Pausar, parar, ocultar | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 2.3.1 | Três flashes ou abaixo do limite | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 2.4.1 | Contornar blocos | Não testado | Skip link no template base e na prévia, navegação real não testada. |
| 2.4.2 | Página com título | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 2.4.3 | Ordem do foco | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 2.4.4 | Finalidade do link (em contexto) | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 2.4.5 | Múltiplas formas | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 2.4.6 | Cabeçalhos e rótulos | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 2.4.7 | Foco visível | Não testado | Foco visível verificado em prévia nos dois temas e cinco larguras. |
| 2.4.11 | Foco não obscurecido (mínimo) | Não testado | Sticky bars e modais em páginas reais sem validação. |
| 2.5.1 | Gestos de ponteiro | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 2.5.2 | Cancelamento do ponteiro | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 2.5.3 | Rótulo no nome | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 2.5.4 | Atuação por movimento | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 2.5.7 | Movimentos de arrastar | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 2.5.8 | Tamanho do alvo (mínimo) | Não testado | Meta de design 44px; exceções de 24px não examinadas em todos os links. |
| 3.1.1 | Idioma da página | Não testado | Documentos HTML verificáveis declaram pt-BR; conteúdo de terceiros não analisado. |
| 3.1.2 | Idioma das partes | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 3.2.1 | Em foco | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 3.2.2 | Ao receber entrada | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 3.2.3 | Navegação consistente | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 3.2.4 | Identificação consistente | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 3.2.6 | Ajuda consistente | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 3.3.1 | Identificação de erros | Não testado | Erros associados ao campo nos formulários cobertos por classes conhecidas; validação real pendente. |
| 3.3.2 | Rótulos ou instruções | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 3.3.3 | Sugestão de erro | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 3.3.4 | Prevenção de erros (legal, financeiro, dados) | Não testado | Exclusões têm confirmação anterior; segurança funcional de fluxos com dados reais não testada. |
| 3.3.7 | Entrada redundante | Não testado | Verificação manual e/ou integrada da jornada real pendente. |
| 3.3.8 | Autenticação acessível (mínimo) | Não testado | Recuperação offline existente; autenticação acessível exige teste com pessoa/TA. |
| 4.1.2 | Nome, função, valor | Não testado | Nomes em controles de templates inspecionados estaticamente; árvore de acessibilidade real pendente. |
| 4.1.3 | Mensagens de status | Não testado | Estados anteriores de modal testados em simulação; leitores de tela não testados. |

*A classificação “Não aplicável” refere-se ao conteúdo inspecionado do ZIP; não certifica integrações externas, uploads de usuário ou alterações posteriores.

Fonte normativa: https://www.w3.org/TR/WCAG22/ e tradução https://www.w3c.br/traducoes/wcag/wcag22-pt-BR/
**Importante:** 2.5.8 AA exige 24×24 CSS px ou exceções, não 44×44; 44px é meta de design do ALECE.
**Nota:** WCAG 2.2 removeu 4.1.1 Parsing (critério obsoleto), por isso ele não aparece na matriz.
