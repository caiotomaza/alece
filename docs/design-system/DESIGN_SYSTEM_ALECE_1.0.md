# ALECE Design System 1.0

**Data:** 2026-10-27 · **Escopo:** estilos compartilhados de Django Templates · **Estado:** consolidação incremental, sem migração de framework.

## Princípios

Manter identidade visual verde ALECE, densidade informacional, funcionalidade financeira, temas claro/escuro controlados por `html[data-theme]`, rótulos, foco navegável, estados informativos e usabilidade em 390–1280 px. As áreas financeiras, permissões e rotas não foram alteradas. A ausência de telemetria externa obrigatória continua vigente. Acessibilidade é alvo técnico WCAG 2.2 AA, não conformidade certificada.

## Arquitetura e ordem de carregamento

1. `finance/alece_tokens.css` — **única fonte** para a paleta ativa, tokens semânticos e aliases legados (`--bg`, `--primary`, `--text` etc.).
2. `finance/alece.css` — arquitetura visual e módulos existentes, mantidos para compatibilidade.
3. `finance/alece_ui_consistency.css` — ajustes específicos já existentes, sem o bloco duplicado de controles em gradiente.
4. `finance/alece_components.css` — componentes semânticos e contratos de geometria/estado aplicados por último.
5. `extra_css` por tela quando existente, para especificidades funcionais.

As páginas standalone login e recuperação carregam tokens antes do CSS específico; a configuração inicial também os carrega. A página de **erro HTTP** permanece com CSS autônomo por resiliência em falhas de infraestrutura (exceção deliberada).

## Catálogo de tokens

| Família | Nomes | Uso |
|---|---|---|
| Cores de superfície | `--ds-color-bg`, `--ds-color-surface`, `--ds-color-muted-surface` | Fundo, card e controle |
| Cores de texto e borda | `--ds-color-text`, `--ds-color-muted`, `--ds-color-border` | Hierarquia e limites |
| Ações | `--ds-color-brand`, `--ds-color-brand-hover`, `--ds-color-on-brand`, `--ds-color-danger`, `--ds-color-on-danger` | Ações normais e destrutivas |
| Estados | `--ds-color-success`, `--ds-color-warning`, `--ds-color-focus`, `--ds-ring` | Feedback, alertas e foco |
| Tipografia | `--ds-font-family`, `--ds-font-body`, `--ds-font-label`, `--ds-font-caption`, `--ds-font-heading` | Texto adaptativo |
| Espaçamentos | `--ds-space-1/2/3/4/5/6/8` | 4, 8, 12, 16, 20, 24, 32 px |
| Arredondamento | `--ds-radius-sm`, `--ds-radius-control`, `--ds-radius-card`, `--ds-radius-dialog` | 8, 12, 17, 18 px |
| Dimensões | `--ds-size-control`, `--ds-size-icon`, `--ds-size-checkbox` | 44, 42, 20 px |
| Visuais | `--ds-shadow-card`, `--ds-control-surface`, `--ds-control-border`, `--ds-select-chevron` | Estados e dropdowns |

As cores legadas efetivamente renderizadas na versão anterior foram mantidas; os tokens semânticos fazem referência à paleta existente, sem substituir a marca.

## Componentes, anatomia, variantes e estados

| Componente | Anatomia | Variantes / estados | Exemplo de marcação |
|---|---|---|---|
| Botão | rótulo/ícone, área interativa, borda, foco | Primária (padrão), secundária, neutra, destrutiva, desabilitada | `<button class="button">Salvar</button>` / `<button class="button danger">Excluir</button>` |
| Botão semântico | mesmo contrato acima | `.ds-button--secondary`, `.ds-button--neutral`, `.ds-button--danger` | `<button class="ds-button ds-button--neutral">Filtrar</button>` |
| Text input / valor | label explícito, campo, erro e ajuda | normal, foco, desabilitado, inválido via mensagem existente | `<label>Valor <input type="number" name="valor"></label>` |
| Select | label, superfície, caret SVG, opções nativas | claro, escuro, desabilitado, foco; múltiplo preserva nativo | `<label>Conta <select><option>Principal</option></select></label>` |
| Checkbox | label associado e quadrado 20 px | selecionado, não selecionado, desabilitado, foco; fallback forced-colors | `<label><input type="checkbox"> Ativo</label>` |
| Radio | label e círculo nativo 20 px | selecionado, desabilitado, foco | `<label><input type="radio" name="periodo"> Mês</label>` |
| Filtro | label, input/select e botão | neutro, foco, desabilitado | `<form class="chart-category-form">…</form>` |
| Tabela | cabeçalho, células, wrapper rolável | largura responsiva e espaçamento lateral preservado | `<div class="table-wrap"><table>…</table></div>` |
| Card | superfície, título, corpo, ações | bloco informativo, métrica ou gráfico | `<article class="card"><h2>Saldo</h2>…</article>` |
| Gráfico | título, área do canvas/SVG, rótulos existentes | tamanho contido no painel, cores legadas preservadas | `<div class="chart-card"><canvas></canvas></div>` |
| Modal | `dialog.unified-dialog`, cabeçalho, formulário, rodapé | aberto, rolável, fechar/cancelar já gerenciados pelo JS | `<dialog class="unified-dialog">…</dialog>` |
| Mensagem | texto e região de feedback | `.success`, `.error`, `.warning`; preservar `role=alert/status` | `<p role="alert" class="message error">Corrija o valor</p>` |

**Não remover** rótulos, `for`/`id`, `name`, validação de formulário, ARIA, classes usadas por eventos ou filtros de perfil financeiro. As classes `ds-button` são opção progressiva; não exigem converter imediatamente os templates.

### Regras e limites

- Controles textuais de linha única: altura mínima 44 px, raio 12 px, borda 1 px, padding horizontal 12 px. Textarea pode crescer verticalmente.
- Botões: 44 px mínimos, raio 12 px; ações destrutivas usam cor negativa, com foreground específico para tema.
- Checkboxes e radios: 20 px, mantendo semântica e interação por teclado; em modo forced-colors os checkboxes recuperam aparência nativa.
- Tabelas: wrapper com padding e overflow horizontal, sem ocultar colunas financeiras.
- Selects: fundo **sólido**, caret consistente, opções nativas com `color-scheme` alinhado ao tema (aparência final depende de navegador/SO).
- Gradiente decorativo do hero e visualizações de dados são exceções justificadas; filtros e campos usam superfícies sólidas.

A revisão de 29/10/2026 passou a servir o CSS público de login e recuperação por `finance/alece_auth.css`, mantendo as regras próprias de configuração inicial e erro crítico. Consulte `REVISAO_CONSISTENCIA_UI_2026-10-29.md` para escopo, validações e restrições.

## Compatibilidade, manutenção e próximos passos

A base CSS histórica mantém seletores especializados para alguns módulos, e parte dos `!important` atende acessibilidade, responsividade, invisibilidade de campos e travamento de modais. **Não foram eliminadas todas as duplicidades ou ocorrências de `!important`** — alterá-las em massa sem validar todas as rotas seria arriscado. Preferir migrar componente por componente, com captura e teste específico, antes de remover regras remanescentes. O novo módulo de componentes não contém `!important`.

### Referências

- MDN: [CSS custom properties](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Cascading_variables/Using_custom_properties) e [color-scheme](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/color-scheme).
- W3C: [WCAG 2.2](https://www.w3.org/TR/WCAG22/), incluindo 1.4.11 (contraste não textual), 2.4.7 (foco visível) e 2.4.11 (foco não ocultado AA).
- Django: [Static files](https://docs.djangoproject.com/en/6.0/howto/static-files/) (a versão de Django instalada em produção deve ser confirmada antes de procedimentos específicos).
- ISO 9241-11, ISO 9241-210, heurísticas de Nielsen e Gestalt: referências de projeto, **não** certificações de conformidade.
