# Regressão de formulários e modais — matriz de cobertura

A **suite Playwright executada** usa fragmentos HTML e respostas HTTP **simulados**. Ela valida o contrato comum do frontend, não o fluxo integrado das views Django/PostgreSQL.

| Área | Criar | Editar | Cancelar | Excluir | Validação HTTP/servidor |
|---|---|---|---|---|---|
| Usuários | Forma HTML comum simulada | Forma HTML comum simulada | Confirmado na simulação | Confirmação JS simulada | Testes Django existentes não executados |
| Perfis financeiros | Forma HTML comum simulada | Forma HTML comum simulada | Confirmado na simulação | Confirmação de exclusão preservada no template | Testes Django existentes não executados |
| Despesas | Forma HTML comum simulada | Forma HTML comum simulada | Confirmado na simulação | `confirm_delete` mantém checkbox obrigatório | Testes Django existentes não executados |
| Investimentos | Forma HTML comum simulada | Forma HTML comum simulada | Confirmado na simulação | `confirm_delete` mantém checkbox obrigatório | Testes Django existentes não executados |
| Integrações de IA | Forma HTML comum simulada | Forma HTML comum simulada | Confirmado na simulação | Confirmação ALECE em `settings_admin_panel` | Testes Django existentes não executados |
| Permissões/senha | Formulários individuais preservados | Mudanças não são salvas em lote | Continuar/Descartar | Exclusão explícita | DB e serviços não validados |
| Pagamentos e estornos | — | Cálculos UI preservados | Confirmação separada de estorno | — | Sem POST automático ao marcar conta; teste integrado pendente |

## Evidência automatizada

- 20 casos de Playwright de diálogos/ações do frontend, inclusive fluxo comum de 5 entidades simuladas, Tab, Escape, backdrop, 403/409/500, confirmação explícita e foco/restauração.
- 10 casos preexistentes do Design System.
- Execução em Chromium real, mas **com respostas simuladas** e sem navegação HTTP real; políticas do Chromium neste ambiente bloquearam conexões/navegações, inclusive `localhost`, por isso a simulação foi usada.
- Testes com Django/PostgreSQL e criação/edição/exclusão dos cinco fluxos reais **PENDENTES**; requisito de aceite completo ainda não cumprido.

## Riscos e pendências

1. **Alto: integração não validada.** Dependências Django e PostgreSQL ausentes neste ambiente. Executar testes de autenticação, permissões, sessão e CRUD contra banco de testes isolado antes da implantação.
2. **Médio: navegação/representação em browsers alternativos.** Só Chromium foi exercitado; testar Firefox, Safari, Android/iOS com leitor de tela e zoom.
3. **Médio: acessibilidade sem JS.** Erros dos templates customizados podem não ter associação programática em todos os campos sem melhoria JS. Auditoria de `aria-describedby` no lado Django pendente.
4. **Médio: modais legados de importação.** Fragmentos independentes têm scripts locais/fechamento próprios, não totalmente migrados; regressão de importação/reconciliação continua necessária.
5. **Médio: testes de atomicidade/CSRF reais pendentes.** Frontend não garante transação; preservar backend como fonte de verdade.
6. **Médio: fluxo sem suporte a `<dialog>`.** Funcionalidade normal do formulário permanece, mas confirmação visual de aprimoramento pode não aparecer.
7. **Baixo: CSS por especificidade.** Novas regras foram acrescentadas por último para preservar Design System 1.0, sem reescrita de cascata histórica.

## Homologação mínima antes de produção

No ambiente **de testes isolado**, reproduzir criar/editar/cancelar/excluir/erro em usuário, perfil, despesa, investimento e IA. Em cada fluxo medir rollback, validação, permissão (403), CSRF, concorrência (409), transação, logs e contexto de perfil; simular navegador sem JS e teclado, touch/viewport pequeno, temas claro/escuro, zoom 200%, Escape e clique fora. Salvar prints com dados fictícios e registrar alterações. Não usar banco de produção para os testes.
