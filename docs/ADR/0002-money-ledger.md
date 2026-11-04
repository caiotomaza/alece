# ADR-0002 — Precisão monetária e ledger auditável

- **Estado:** Aceita como invariante alvo
- **Data:** 2026-10-15
- **Decisão:** Decimal como fonte de verdade, operações idempotentes, débito e lançamento na mesma transação de DB, proibição de saldo negativo, saldo desconhecido distinto de zero, estorno por lançamento compensatório e não exclusão de eventos imutáveis.
- **Estado do código:** serviço inicial `confirm_outflow` com locking e batch/legs está presente. Estorno completo, conciliação/importação e ajustes automáticos de todos os tipos de movimento **não estão implementados**. Exigir conclusão antes de uso financeiro real.
