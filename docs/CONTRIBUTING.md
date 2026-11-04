# Contribuindo com ALECE

Leia antes os documentos de arquitetura, domínio, design system e licença. Aceitamos correções pequenas, documentadas e reversíveis.

O contrato vigente tem cinco destinos principais: Visão geral, Despesas, Investimentos, Movimentações e Configurações. O HTML `docs/prototype/ALECE_Prototipo_Visual_v1.32.1.html` é referência visual imutável; templates e CSS ativos ficam em `src/view/templates/` e `src/view/static/`. Revise `docs/reviews/ALECE_REVISAO_ARQUITETURA.md` antes de alterar o ledger, importações ou autorizações.

Para mudanças de interface, compare o protótipo e a aplicação com dados sintéticos nos temas Claro/Escuro e em 320, 390, 768 e 1440 px. Os scripts `scripts/visual_compare.py`, `scripts/visual_modal_compare.py` e `scripts/e2e_visual_audit.py` registram dimensões, capturas, persistência e permissões no banco de auditoria isolado. Mantenha as imagens fora do Git e documente diferenças reais em `docs/reviews/ALECE_VALIDACAO_VISUAL_V1.32.1.md`.

1. Abra Issue com reprodução, logs **sem segredos** e ambiente, especialmente se houver efeito financeiro.
2. Abra PR em branch específica, evite refatorar e mudar finanças simultaneamente.
3. Inclua testes de cálculo/ACL/DB; migrações versionadas quando necessário.
4. Atualize README/RUNBOOK/ROADMAP e docs/CHANGELOG.md se o comportamento mudar.
5. Descreva riscos, backup anterior, plano de rollback e validação do release.
6. Não remova histórico de movimentações ou backups silenciosamente.

Ao contribuir, você declara ter direito de licenciar sua contribuição sob GNU GPL v3 aplicável ao projeto. Não submeta marca ou componente de terceiro sem licença compatível e autorização.

## Mudanças de performance/UX

Não apresentar ganho estimado como medido. Para cada PR, registrar ambiente (Django/PostgreSQL/Chromium), cenário com dados sintéticos, baseline revisada, amostra, mediana/p75, delta e logs sem dados financeiros. Conferir `docs/performance/USABILIDADE_ROTEIROS_E_METRICAS.md` e `docs/qualidade/DEFINITION_OF_DONE.md`. Se a comparação ponta a ponta não for possível, marcar como **pendente**.
