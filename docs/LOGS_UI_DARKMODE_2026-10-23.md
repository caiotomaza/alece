# Ajuste visual de Logs e correção de dropdowns no dark mode

Data: 2026-10-23 23:36:15

## Alterações

- Padronização completa da tela **Logs do Sistema** com o mesmo estilo das demais seções do ALECE.
- Filtros reorganizados com alinhamento, tipografia e espaçamentos consistentes.
- Tabela refeita com moldura interna, respiro lateral nas colunas e botão de detalhes compatível com o tema.
- Correção global para leitura de opções de `<select>` no **modo escuro** e no **modo claro**, incluindo `option` e `optgroup`.
- Ajuste de `color-scheme` para `select` e `input[type=date]`, melhorando os controles nativos do navegador.

## Arquivos alterados

- `src/view/templates/core/system_logs_list.html`
- `src/view/static/finance/alece.css`

## Observações

- Não houve alteração de banco de dados nem migrations.
- O comportamento dos filtros e do detalhamento de logs foi preservado, apenas com melhoria visual.
- A validação funcional completa em Django/PostgreSQL continua dependente do ambiente final.
