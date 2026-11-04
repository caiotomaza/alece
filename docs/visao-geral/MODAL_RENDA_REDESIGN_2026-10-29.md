# ALECE — Redesenho do modal de renda (29/10/2026)

## Objetivo e base

Base **exclusiva**: `ALECE_COMPLETO_CAMPO_RENDA_PADRONIZADO_2026-10-28.zip`, SHA-256 `d08f2c38024294d35634a9090f1a0a53a2e19988ecc8674a88e5d3a38c6ed195`, verificado antes da intervenção. O arquivo original permanece preservado em `$HOME/backups` com `.sha256` validado. Nenhuma instância PostgreSQL ou instalação de produção foi acessada.

## Alterações

- Redesenhado o componente na estrutura **cabeçalho, lista de perfis e rodapé**, utilizando os tokens do Design System ALECE 1.0 (`--ds-*`), as cores dos dois temas e a geometria de botões e campos dos demais modais.
- Removida a altura mínima artificial de 300 px e a divisão visual que fazia `R$` parecer um campo separado. O modal cresce com as linhas e possui limite por viewport e rolagem interna quando necessário.
- O título e o botão de fechar fazem parte do cabeçalho. O botão de fechar é exibido apenas quando o JS do modal está ativo; sem JavaScript, a página de fallback mantém o link Cancelar e o formulário POST.
- Os controles exibem valores no formato **2.300,00** (pt-BR) com prefixo visual `R$`. No envio, o `FormData` normaliza a quantia para a representação decimal que o Django já recebe (`2300.00`). A normalização não altera `name`/IDs, endpoint, CSRF, modelos, permissões, validação nem o fluxo de transação atômica do servidor. Valores inválidos são preservados para o backend validar; valores vazios mantêm a semântica anterior.
- Foco inicial no título, indicador de foco visível somente durante navegação de teclado nos campos, restauração de foco ao fechar, cancelamento com alterações não salvas e apresentação de erros por campo.

## Arquivos de produção alterados

- `src/view/templates/finance/_income_bulk_form.html`
- `src/view/static/finance/alece_overview.css`
- `src/view/static/finance/alece_overview_income.js`

Não houve alteração de `models.py`, migrations, serviços financeiros, rotas, Docker Compose, `.env` ou `.env.example`.

## Testes e evidências

Os scripts `scripts/quality/test_income_redesign_preview.py` (novo), `verify_income_currency_ui.py` e `test_income_popup_preview.py` (atualizados) utilizam Chromium em **fixture HTML sintética**, incluindo duas cores, 320, 390, 768, 1280 e 1920 CSS px, navegação com Tab, formato local, serialização do valor, fechamento e simulação de erro 422. As quatro capturas novas em `docs/visao-geral/evidencias/renda_redesign_*.png` pertencem à fixture — não são screenshots de uma página autenticada. As capturas anteriores `renda_modal_*_preview.png` continuam preservadas como referência histórica.

Testes Django/PostgreSQL permanecem **não executados** por indisponibilidade dessas dependências neste ambiente. Não se declara a aplicação homologada em produção apenas com a regressão estática/de interface isolada.

## Riscos residuais / aceite em homologação

- Verificar POST real com um e vários perfis autorizados, incluindo `R$ 2.300,00` apresentado e `2300.00` persistido, valores vazios e zero, e erros 403/409/422.
- Verificar operações sem JavaScript pela URL normal do formulário.
- Validar captura autenticada em navegadores reais, teclado, NVDA/VoiceOver/TalkBack e zoom 200%/400%.
- Verificar rollback transacional e ausência de alteração inadvertida de perfis sem permissão.

## Atualização e rollback

1. Fazer backup verificável do código e do `.env` **da instalação de destino**, além de backup nativo verificado do PostgreSQL e volumes persistentes. Não incluir secrets em logs ou enviar `.env` a terceiros.
2. Conferir o `.sha256` do ZIP novo e extrair **os arquivos do ZIP diretamente** na pasta `alece`, preservando o `.env` produtivo. Reconstruir/recriar somente o serviço `web` conforme `compose.yaml`, sem `down -v`, `volume prune` ou limpeza de dados.
3. Homologar a abertura do modal, os dois temas, o salvamento de rendas fictícias em banco isolado e os logs do serviço.
4. Se houver regressão, restaurar o código e os estáticos do ZIP de origem ou backup validado e reconstruir apenas `web`. Como não existem migrations nem alterações persistentes nesta entrega, **não restaurar automaticamente o banco**. Preservar logs e backups.

Referências de engenharia: WAI-ARIA APG Dialog Modal Pattern (https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/), MDN HTML dialog (https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/dialog), Django 5.2 Forms DecimalField (https://docs.djangoproject.com/en/5.2/ref/forms/fields/).
