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
- Reserva: meta por 9 meses de despesas essenciais (configurável 6–12), saldo já acumulado independente da meta.
- Checkbox de Este mês: consultar batch do mês; marcar gera grupo/legs por origem, desmarcar gera **novo grupo de estorno** (nunca apagar as legs originais).
- `TransactionBatch.idempotency_key`: não tratar duas confirmações da mesma operação como novos débitos.

## Políticas de cálculo

```text
reserva_meta = despesas_essenciais_previstas × meses_de_protecao
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
