# ALECE — Definition of Done (performance/UX)

Uma alteração é considerada **pronta para homologação** somente se:

- [ ] Problema e risco foram reproduzidos em ambiente identificado; perfis/permissões e dados financeiros preservados.
- [ ] Baseline antes e depois é da **aplicação Django real** com fixtures sintéticas, no mesmo ambiente; métricas indisponíveis marcadas como pendentes.
- [ ] Logs não contêm segredos, SQL com parâmetros, credenciais ou saldos desnecessários.
- [ ] Testes ORM, HTTP, navegação, temas, responsividade e autorização executados (ou impedimento justificado).
- [ ] Se mudança SQL: `EXPLAIN ANALYZE`/contagem e consultas N+1 avaliados; não criar índice sem necessidade comprovada.
- [ ] Se mudança de interface: erros, estados vazios, loading, keyboard, foco e confirmações sensíveis preservados.
- [ ] Relatório de Core Web Vitals separa p75 de campo de dados de laboratório; INP não substituído por TBT arbitrariamente.
- [ ] Testes de usabilidade registram separadamente conclusão, erros, tempo e satisfação; dados pessoais minimizados.
- [ ] Backup com SHA-256, log, testes pós-alteração e rollback disponíveis; nenhum artefato apagado automaticamente.
- [ ] CI, documentação e changelog atualizados; aprovação manual de capturas visuais.

**Não atendidos nesta rodada:** baseline temporal no Django, execução PostgreSQL do teste SQL, teste humano de usabilidade; bloqueiam alegações de melhoria medida e homologação produtiva.
