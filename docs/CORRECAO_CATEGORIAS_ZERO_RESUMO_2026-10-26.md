# Correção: ocultar categorias zeradas no resumo de renda

## Escopo

Página `/visao-geral/` > cartão **Resumo** > gráfico de distribuição da renda.
A legenda e os segmentos do donut devem apresentar exclusivamente categorias com valor **positivo**. Valores monetários e demais somatórios não foram alterados.

## Implementação

- `src/controller/apps/finance/services/metrics.py`: `aggregate_income_plan` descarta categorias `value <= Decimal("0.00")` da lista de apresentação e dos segmentos do gráfico.
- `src/view/templates/finance/workspace_page.html`: metadado identifica despesa/investimento por `category.source`, não pela posição na legenda. Renderiza mensagem de estado vazio quando todas as categorias ficam zeradas.
- `tests/finance/test_visual_read_models.py`: regressões para combinação de categorias positivas e zeradas e cenário totalmente zerado.

## Comportamento esperado

- `R$ 0,00`: oculto da legenda e do donut (sem fatia ou marcador).
- Valor positivo: visível, inclusive quando é a única categoria positiva.
- Todas as categorias sem valor: donut neutro e mensagem `Nenhuma categoria com valor positivo nesta distribuição.`
- Renda desconhecida: permanece o estado desconhecido existente.
- Somatórios, permissões, cadastros, movimentações e outros painéis não sofrem alterações.

## Verificação funcional

1. Abrir `/visao-geral/` com perfil que possui renda, despesas e distribuição sugerida.
2. Confirmar que `Discricionárias`, `Imprevisíveis` e `Reserva` com `R$ 0,00` não aparecem na legenda.
3. Confirmar que itens com valores positivos permanecem e a identificação despesa/investimento está correta.
4. Em teste com categorias todas zeradas, confirmar mensagem de estado vazio e ausência de fatias coloridas.
5. Executar os testes `tests/finance/test_visual_read_models.py` em **banco de testes isolado**.

## Implantação e rollback

- O pacote é o projeto completo, para extrair na raiz da instalação ALECE sem pasta extra.
- Antes de substituir arquivos, gerar backup dos arquivos modificados e validar SHA-256, preservando também `.env`, banco PostgreSQL e volumes.
- A alteração não requer migration.
- Depois de substituir, reconstruir apenas o serviço web (não remover volumes).
- Rollback: restaurar os dois arquivos do código, além do teste, a partir do backup anterior à substituição, verificar SHA-256 e reconstruir o serviço web. Para rollback integral, utilizar o ZIP completo anterior.

## Limite da validação

A lógica pura da função pode ser testada isoladamente; a execução real Django/PostgreSQL requer ambiente de testes e não deve ser inferida apenas de verificação estática.
