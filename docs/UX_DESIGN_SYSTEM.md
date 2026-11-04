# Sistema visual ALECE — regra de consistência

A referência visual primária está em `docs/prototype/ALECE_Prototipo_Visual_v1.32.1.html`. Ela não é código de produção; é um **contrato visual** a ser portado em componentes reutilizáveis com testes responsivos e de acessibilidade.

**Estado de 23/10/2026:** o shell ativo tem cinco destinos (Visão geral, Despesas, Investimentos, Movimentações, Configurações), temas Claro/Escuro, ações `+`, lápis e formulário em modal com rodapé. A fidelidade completa ainda não foi validada em 320/390/768/1440 px nos dois temas; consulte `docs/reviews/ALECE_VALIDACAO_VISUAL_V1.32.1.md`. Os componentes abaixo são um contrato de evolução, não uma lista de componentes já implementados.

- Apenas **Claro** e **Escuro**; tokens centralizados, não valores hex espalhados nos componentes.
- Padrões de navegação, cards, tabelas, ordenação, gráficos, menus e modais reutilizados em todas as abas.
- Item novo: `+` no cabeçalho da seção; item existente: lápis; exclusão e salvar ficam **dentro do mesmo modal** no rodapé alinhado à direita.
- Modal de despesa previsível: **Excluir · Cancelar · Confirmar pagamento · Salvar e fechar**; não introduzir dropdown de operação CRUD dentro do modal.
- Despesa imprevisível lançada por `Este mês`: só **perfil, nome e valor**; categoria Imprevisíveis e mês atribuídos pelo sistema.
- Checkbox de confirmação: modal com uma ou várias origens e saldos insuficientes tratados, sem transição silenciosa.
- Zero e desconhecido têm semânticas diferentes. Ocultar linhas sem valor, mas oferecer recuperação e acesso a histórico.
- Mobile: evitar scroll global horizontal, permitir scroll local em tabelas. Mínimo touch target adequado, keyboard e foco.
- Gráficos e estados não podem depender **somente** de cor; contraste e navegação por teclado devem ser validados.

Componentes planejados: `PageShell`, `FinancialProfileSwitcher`, `ThemeToggle`, `MetricCard`, `SortableTable`, `EditIconButton`, `CreateIconButton`, `UnifiedDialog`, `MoneyInput`, `MonthChecklist`, `AccountOriginDialog`, `ReserveGoalCard`, `PeriodChart`.

## Densidade e fluidez sem comprometer confirmação

Evitar reflow durante carregamento, manter feedback de submit, foco visível e estado de carregamento acessível. Nunca suprimir rótulos, confirmações financeiras, verificações de permissão ou conteúdo no mobile para ganhar velocidade aparente. Consultar `docs/performance/USABILIDADE_ROTEIROS_E_METRICAS.md` antes de alterar fluxos.
