# Funcionamento esperado da ferramenta

ALECE oferece gestão financeira pessoal e familiar self-hosted, com até **cinco perfis financeiros por núcleo**, usuários Administrador e Comum, permissões granulares de visualizar/editar perfis financeiros e visão individual/combinada. **Nome** em homenagem a Alice, profissional da área de economia.

## Navegação e consistência visual

- Sidebar à esquerda: **Visão geral, Despesas, Investimentos, Movimentações, Configurações**, com seletor de perfil; **Sobre o projeto** por ícone contextual.
- Light e Dark Mode, paleta verde, neutros e dourado moderado; componentes idênticos nas páginas.
- Botão `+` no cabeçalho de cada área cria; **lápis** nas linhas edita; modal padrão com **Excluir, Cancelar e Salvar e fechar**. Pagamentos confirmados usam o fluxo explícito de seleção de origem.
- Tabelas com ordenação por cabeçalho; maior valor primeiro por padrão; responsividade real mobile/tablet.
- Valores financeiros zero/vazios não poluem gráficos/legendas. **Zero não é saldo desconhecido**.

## Visão geral

- **Saldo:** contas/bancos/dinheiro físico do perfil selecionado. Entradas sem valor conhecido ou com saldo zero podem ficar ocultas, **sem exclusão automática de dados históricos**.
- **Resumo circular:** renda do mês como base de 100%, categorias de despesas e **aplicações mensais recomendadas**. Nunca misturar patrimônio acumulado com renda mensal.
- **Este mês:** despesas previsíveis individuais (Essenciais, Estratégicas, Discricionárias), despesas imprevisíveis extras e recomendações de aplicações com meta. Cada checkbox de confirmação exige origem: uma ou várias contas. Débito + histórico atômico, sem saldo negativo, com rollback/estorno auditável. Saldo projetado = saldo atual - compromissos **pendentes**.

## Despesas

- Previsíveis: nome, categoria, valor e **dia obrigatório** do mês, sempre mensal. Exibir pagamento por mês e situação (pendente, parcial, pago) calculada por movimentos vinculados, nunca por texto livre.
- Imprevisíveis: cadastrar só nome e valor; data/mês registrados pelo servidor. CRUD com limites quando já houver pagamento. Sem inventar categoria fixa ou periodicidade no formulário simplificado.

## Investimentos

Categorias fixas:
1. Desenvolvimento pessoal e profissional
2. Aquisição patrimonial
3. Consumo planejado
4. Reserva

Posições financeiras: nome, instituição, aplicado, valor atual e meta opcional (exceto meta monetária da Reserva, calculada pelo sistema).

**Reserva:** meta = soma das despesas essenciais mensais × 6–12 meses, **9 por padrão**. Se já atingida, não receber aplicação sugerida e não aparecer como obrigação na Visão geral. Aplicações mensais são sugestões, não ordens para o banco.

O valor disponível após despesas e obrigações confirmadas vai prioritariamente para cobrir lacuna da Reserva; o restante é distribuído por pesos aos três objetivos. Estimativa em meses sem projetar rendimento futuro salvo configuração metodologicamente explícita.

## Movimentações

- Entradas e saídas manuais com conta de origem/destino, data, estado, vínculo a despesa/investimento.
- CSV: upload, análise por adaptadores de banco, prévia, sugestão com nível de confiança, edição humana e confirmação idempotente.
- PDF real: requisito futuro. Processar em sandbox, limites de tamanho/tempo, tipos de arquivo, extração segura; não afirmar que leu documento não interpretado.
- Toda reversão permanece auditável; não excluir dinheiro do passado por alteração de interface.

## Configurações

Criar até 5 perfis, permissões por usuário, temas, saldo de referência, coeficiente de Reserva, administração de credenciais. Login por usuário/senha e código único de recuperação **é requisito, não implementação no starter**.

## Diferença entre protótipo e código do ZIP

A referência HTML tem interações demonstrativas sem backend. O código Django entregue nesta base tem **somente um subconjunto** da funcionalidade: modelos, cálculos, serviço de saída de caixa e pontos de saúde. Leia `docs/ROADMAP.md` antes de apresentar o produto como concluído.
