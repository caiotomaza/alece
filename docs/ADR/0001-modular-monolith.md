# ADR-0001 — Monólito modular Django

- **Estado:** Aceita como decisão inicial
- **Data:** 2026-10-15
- **Contexto:** app financeiro self-host em servidor pessoal/ZimaOS, pequenas equipes e perfis familiares; transações de débito exigem integridade e deploy simples.
- **Decisão:** Django monólito modular + PostgreSQL + Docker Compose, domínio puro para cálculos e serviços transacionais para mutações; templates no início e frontend progressivo a ser definido.
- **Alternativas rejeitadas:** microsserviços (overhead de operação e transações distribuídas), frontend totalmente separado desde o primeiro commit (complexidade sem requisito técnico comprovado).
- **Consequências:** menos componentes operacionais, migrations centralizadas, possibilidade de extrair módulos depois mediante contratos de serviço e eventos controlados. Nova arquitetura exige novo ADR e testes de migração.
