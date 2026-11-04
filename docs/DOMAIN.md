# Núcleo financeiro — invariantes não negociáveis

## Representação

- Persistir valores monetários como **DecimalField (duas casas)**, nunca `float` como fonte de verdade.
- Renda (`FinancialProfile.monthly_income`) pode ser `NULL` = desconhecida ou `0.00` = zero informado.
- Saldo (`BankAccount.balance`) pode ser `NULL` = desconhecido ou zero; saldo zero pode ocultar conta da **visualização**, mas não provocar exclusão física.
- Saldo atual da conta não é renda; soma de saldos não deve ser somada à renda como dinheiro novo.
- Somas devem ser restritas a `Workspace` + perfis aos quais o usuário tem acesso.

## Fluxos

- Despesa previsível: referência mensal independente de pagamento (a existência da conta não implica quitação).
- Despesa imprevisível: fato do mês; nome e valor; pode estar pendente ou vinculado ao pagamento; confirmar débito por origem.
- Aplicação: mover recursos de conta para posição de investimento, **não** despesa de consumo.
- Reserva: meta por 9 meses, por padrão, da soma de **todas** as despesas previsíveis ativas (Essenciais, Estratégicas e Discricionárias) com a média mensal de **todo o histórico de despesas imprevisíveis cadastradas** do mesmo perfil (configurável de 6 a 12 meses). O saldo já acumulado permanece independente da meta.
- Checkbox de Este mês: consultar batch do mês; marcar gera grupo/legs por origem, desmarcar gera **novo grupo de estorno** (nunca apagar as legs originais).
- `TransactionBatch.idempotency_key`: não tratar duas confirmações da mesma operação como novos débitos.

## Políticas de cálculo

```text
media_imprevisiveis = arredondar_centavos(soma_das_imprevisiveis_registradas / numero_de_meses_distintos_com_registros)
# Sem meses registrados, média = 0; todos os lançamentos do mesmo mês entram na soma desse mês.
base_reserva = essenciais_previstas + estrategicas_previstas + discricionarias_previstas + media_imprevisiveis
reserva_meta = base_reserva × meses_de_protecao
lacuna_reserva = max(0, reserva_meta - reserva_atual)
livre = max(0, renda - essenciais - estrategicas - discricionarias - imprevisiveis_confirmadas)
aplicacao_reserva = min(livre, lacuna_reserva)
restante = livre - aplicacao_reserva
restante → divisao ponderada exata em centavos entre os 3 objetivos
saldo_projetado = soma_saldos_conhecidos - total_pendente_mes
```

**Aviso:** verba discricionária já orçada não deve ser somada novamente às despesas discricionárias previsíveis se representar o mesmo envelope. Ao migrar a planilha histórica, definir explicitamente a política de teto para esse envelope. Serviço de cálculo puro do starter recebe valores **já reconciliados**; não deve decidir esse teto automaticamente por suposição.

## Integridade de transação

`confirm_outflow` verifica antes de gravar: perfil, saldo disponível, contas válidas do perfil e idempotência. Tranca linhas de conta com `select_for_update`, desconta o saldo, grava batch e legs na mesma transação. O serviço **não** implementa ainda estorno nem conciliação oficial de investimentos. Não operar dados financeiros reais usando este starter como produto final.

## Cadastros e consultas do Sprint 02

- Cinco perfis **ativos** por núcleo, com lock no workspace para criação/reativação. Arquivados conservam histórico e podem ser consultados, mas não recebem novos cadastros.
- Administrador vê e configura todos os perfis do próprio núcleo. Usuário Comum depende de grant para leitura/edição. A renda nula é desconhecida; `0.00` é zero informado. Editar renda não altera saldos.
- Conta nula é saldo desconhecido; a soma de saldos conhecidos é apresentada separadamente da renda. Conta/posição ligada a movimentação não pode ter valor histórico sobrescrito por formulário.
- Cadastro de despesa previsível ou imprevisível não gera pagamento. Imprevisível recebe data do servidor. Vencimento 29–31 em mês curto é apresentado no último dia válido do mês.
- `profile_summary()` agrega só um perfil autorizado pela view: Reserva = (todas as previsíveis ativas + média das imprevisíveis dos meses distintos com registros) × meses (6–12, padrão 9); atual = posições ativas da categoria Reserva; falta = `max(0, meta - atual)`. A sugestão mensal usa `allocate_monthly` com renda e despesas previsíveis conhecidas e imprevisíveis confirmadas, priorizando Reserva. Despesas pendentes são exibidas separadamente. Sem renda ou despesa previsível cadastrada, nenhuma sugestão mensal é apresentada; a meta da reserva é calculada independentemente da renda quando há acesso a despesas e investimentos. Meta atingida resulta em sugestão zero.
- Visão combinada soma indicadores **já calculados por perfil autorizado**, preservando perfis isolados. Não funde contas, grants, posições ou histórico.

## Atualização de regra de reserva — 2026-11-04

A média de despesas imprevisíveis usa **todos os meses distintos com registros existentes** na tabela `UnexpectedExpense` do perfil, agrupados por `recorded_on` (ano e mês). Cada mês com registro conta uma vez no divisor, mesmo se contiver vários lançamentos. Meses sem registro não entram no divisor; ausência total de histórico produz média zero. A média é arredondada a dois decimais (`ROUND_HALF_UP`) **antes** de somar as previsíveis e multiplicar pelos meses configurados. Cadastros pendentes também entram no histórico da reserva; pagamentos/estornos não criam uma segunda despesa na base.

Exemplo: (R$ 532,90 + R$ 444,28 + R$ 333,33 de média de R$ 1.000,00 registrados em três meses) × 7 = **R$ 9.173,57**. A sugestão de aplicação permanece separada da meta e não movimenta contas. Despesas imprevisíveis confirmadas do mês ainda podem reduzir o orçamento mensal disponível, sem serem somadas novamente à meta.
