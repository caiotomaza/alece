# Inventário de conflitos e rastreabilidade — Design System ALECE 1.0

| Achado anterior | Evidência na versão de entrada | Intervenção | Estado / risco residual |
|---|---|---|---|
| Tokens duplicados em várias camadas | `alece.css` com duas paletas sucessivas; `alece_ui_consistency.css` redefinia superfície/marca; login e recuperação repetiam paleta inline | `alece_tokens.css` recebe **as cores efetivas** anteriores; removidas definições concorrentes em base, consistency e autenticação | Resolvido na rota principal e 3 páginas de autenticação; erro HTTP permanece standalone intencionalmente |
| Filtros e inputs com gradientes | Formulários, `.month-ref-control`, `.chart-category-form` e `.settings-table-scroll` usavam declarações em gradiente conflitantes | Superfícies sólidas para filtros/controles com dimensões unificadas; gradientes de hero e dados preservados | Ajustes específicos adicionais ainda existentes em CSS histórico precisam de validação em todas as telas |
| Uso de `!important` contra select e checkboxes | CSS `alece_ui_consistency.css` com **67 ocorrências** | Substituição de blocos duplicados de select, checkbox e filtros por componente reutilizável; **24 ocorrências** remanescentes no CSS de consistência | Parcial; importantes de layout, visibilidade, scroll lock e exceções não foram removidos indiscriminadamente |
| Várias anatomias para checkbox | Regra global, regras de formulários e regra específica de modal com checkmark distinto | Contrato com 20 px, superfície sólida, checked, teclado e forced-colors | Validado na prévia; verificar modais reais e formas específicas |
| Divergência entre tamanhos de botão/input | Na prévia original: botão 42 px desktop / 41 px mobile; campos 46 px | Controle unificado 44 px, raio 12 px | Aprovado em 4 combinações do catálogo Chromium; faltam telas reais |
| Caret com cores e imagens diferentes | Selects de conta, categoria, IA e autenticados tinham SVG distintos com prioridade elevada | `--ds-select-chevron` por tema; mesmo SVG sem gradiente | Confirmado na amostra do Chromium; opções nativas variam por SO |
| Ação destrutiva sem aparência própria | `.button.danger` não compartilhava contrato claro em diferentes telas | Variante semântica, cores de foreground para light/dark | Confirmar contraste e reconhecimento em fluxos destrutivos reais |
| Espaçamento de tabelas e status | Wrappers de tabela com gutters diferentes; `.message` divergente | Gutter comum em tabela direta, status `success/error/warning` | Verificar tabelas extensas e layout mobile real |
| Foco invisível em CSS histórico | Primeira execução do teste de navegador falhou nos quatro cenários (`outline: none`) | Regra específica de `:focus-visible` aplicada após CSS histórico | 4 reexecuções aprovadas, incluindo foco programático em input de texto |

## Comparação de dívida CSS

`alece.css` conserva 29 ocorrências de `!important` (não alteradas) e os gradientes passam de 18 para 8. `alece_ui_consistency.css` passa de 67 para 24 ocorrências de `!important`, e de 7 para 0 declarações de `linear-gradient`. O novo `alece_components.css` não contém `!important`. Estes indicadores não substituem auditoria semântica, contraste, inspeção de CSSOM ou testes nas telas reais.

Não foram alterados lógica Django, arquivos JavaScript, rotas, migrations ou definições financeiras. O histórico da versão permanece disponível no ZIP anterior preservado com SHA-256.
