# Roadmap por gates — sem prometer produto pronto

| Etapa | Entrega | Critério de aceite |
|---|---|---|
| 0 — Base (starter) | Módulos, modelos, migrações, cálculos, serviço de saída, Compose, CI, docs | Testes CI + build + migrations em ambiente real |
| 1 — Autorização | Login usuário/senha, papel administrador/comum, código de recuperação offline, isolamento workspace/profile | testes de acesso indevido, auditoria e recuperação |
| 2 — CRUD | Renda zero/nula, contas, despesas, metas e investimentos com views e serviços | operações end-to-end + atualização correta em DB |
| 3 — Ledger | pagar por uma/múltiplas contas, estorno imutável, parcelados e transferências | zero double count, conciliação e atomicidade |
| 4 — Importação | adaptadores CSV, staging, deduplicação, preview, confirmação | nenhuma alteração antes da revisão, arquivos adversariais |
| 5 — PDF | leitor PDF seguro, OCR isolado quando indispensável | metadados de origem, limites, testes com dados inválidos |
| 6 — Interface | migrar design v1.32.1 para componentes reais responsivos | teclado, WCAG, iOS/Android/mobile/desktop |
| 7 — Operações | backup de mídia, restore exercitado, release assinada, SBOM, métricas/alertas | teste de desastre com RPO/RTO definido |
| 8 — ZimaOS | integração por GHCR, Compose compatível com instalação customizada | atualização reversível no hardware alvo |

**Bloqueadores antes de produção:** migração/revisão de dados reais, autenticação/autorizações testadas, importadores seguros, LGPD/retention, restore testado, lock de dependências, CI real e hardening de rede.
