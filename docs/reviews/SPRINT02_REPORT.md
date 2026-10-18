# Sprint 02 — relatório de implementação (2026-10-18)

**Decisão: SPRINT 02 APROVADO PARA REVISÃO.** O módulo de cadastros e consultas financeiras está persistido, autorizado por objeto e validado em PostgreSQL isolado. Esta decisão não aprova implantação nem migração de dados reais. A auditoria e o Gate A que antecederam este trabalho estão em `docs/reviews/SPRINT01_AUDIT.md`.

## Entrega funcional

- Após login, o usuário escolhe um núcleo ao qual pertence. Administradores consultam todos os perfis do próprio núcleo; usuários comuns veem apenas os perfis com grant válido. Criar, editar, arquivar e reativar perfis usa bloqueio da linha do núcleo e limite de cinco **ativos**, inclusive sob concorrência. Nome e emoji são editáveis. Perfis arquivados preservam contas e histórico; reativação verifica novamente o limite.
- A tela de perfil lista contas bancárias e dinheiro físico, inclusive arquivados, e permite cadastrar, editar, arquivar ou excluir apenas cadastros sem histórico. Saldo `NULL` significa desconhecido e não se confunde com `0,00`. Renda também pode ser ausente, zero ou positiva; editar ou limpar renda não cria transação.
- Visão geral, Despesas e Investimentos aceitam seleção individual/combinada de perfis ativos autorizados e filtro mensal. IDs alheios ou mês inválido recebem HTTP 400; workspace fora da associação recebe HTTP 403. A soma apresenta rendas conhecidas e contagem de rendas desconhecidas separadamente de saldos conhecidos e desconhecidos.
- Despesas previsíveis têm categorias fixas, valor positivo e vencimento de 1 a 31 (último dia válido nos meses curtos). Despesas imprevisíveis recebem data do servidor e são consultadas por mês. Cadastro e edição não confirmam pagamentos nem debita contas.
- Posições de investimento têm quatro categorias fixas, valor aplicado, valor atual, instituição, data opcional e meta opcional para as três categorias de objetivos. A Reserva usa meta calculada por despesas essenciais mensais × meses de proteção (padrão 9; administrador pode escolher 6–12). A sugestão mensal prioriza cobrir a Reserva; ao completar a meta, sua sugestão é zero e ela continua visível. Prazos sem meta ou aporte positivo não são inventados.
- A interface usa a identidade do protótipo em `reference/prototype/`, sidebar, temas Claro/Escuro, seleção de perfis, ícone `+` por seção, lápis nas linhas, modal progressivo com ações no rodapé e confirmação de exclusão. Sem JavaScript, o formulário permanece uma página normal. O backend confirma a gravação antes do redirecionamento.

## Código, dados e migrações

Os principais arquivos da implementação são `apps/finance/views.py`, `urls.py`, `forms.py`, `query_forms.py`, `services/profiles.py`, `services/accounts.py`, `services/records.py`, `services/metrics.py`, `domain/calculations.py`, `domain/planning.py`, `models.py`, `templates/finance/*` e `static/finance/*`. Views fazem a autorização e o filtro; serviços transacionais persistem; o domínio calcula com `Decimal` e arredondamento explícito. `apps/core/permissions.py` aplica associação ao núcleo e grant por perfil a cada requisição. O Django Admin financeiro ficou somente leitura para impedir bypass dos serviços. Não foram adicionadas dependências de aplicação; a imagem atualiza `pip` para uma versão corrigida antes de instalar as faixas declaradas.

`apps/core/migrations/0002_authenticationattempt.py` suporta a correção de recuperação do Gate A. `apps/finance/migrations/0002_sprint02_catalogs.py` adiciona `FinancialProfile.is_archived`, `InvestmentPosition.recorded_on`, `ck_recurring_due_day_range` e `ck_reserve_no_manual_target`. FKs existentes preservam vínculos do ledger; serviços recusam exclusão com histórico. A criação/reativação usa `select_for_update` sobre o núcleo; a garantia depende de PostgreSQL e da via de serviço, não de escritas SQL arbitrárias.

A migração financeira foi exercitada em banco PostgreSQL efêmero: upgrade, downgrade e re-upgrade passaram com perfil legado preservado. Uma posição legada da categoria Reserva com `target_amount` preenchido fez a migração falhar **sem alterar a linha**, como exige a nova constraint. Antes de aplicar a migração a qualquer base persistente, fazer backup próprio do banco e consultar a contagem de `finance_investmentposition` onde `category='reserve' AND target_amount IS NOT NULL`; revisar esses registros manualmente. O downgrade do schema depois de uso real remove `is_archived` e `recorded_on` e, portanto, perde esses dois estados; rollback de produção exige plano de dados, não apenas `migrate finance 0001`.

## Evidência de validação

| Verificação | Resultado |
|---|---|
| `pytest -q -p no:cacheprovider --tb=short` | **90 coletados, 90 aprovados, 0 falhas, 0 ignorados**, 8 subtestes aprovados, PostgreSQL 16; 47 avisos de pasta `staticfiles` ausente no bind de testes, sem falha funcional. |
| `python manage.py check` | 0 problemas. |
| `python manage.py makemigrations --check --dry-run` | Sem divergência de modelos. |
| `ruff check .` e `git diff --check` | Aprovados; Git informou apenas normalização CRLF/LF no Windows. |
| Migração `finance.0002` em PostgreSQL isolado | Upgrade/downgrade/re-upgrade aprovados; legado inválido rejeitado sem corrupção. |
| `docker build -t alece:sprint02-local .` | Aprovado; 129 arquivos estáticos copiados, 387 pós-processados. Imagem somente local. |
| `pip-audit` de `requirements/production.txt` e de `pip==26.2.1` | Nenhuma vulnerabilidade conhecida para as versões resolvidas em 2026-10-18. A imagem construída confirmou `pip 26.2.1`. |
| QA visual Edge local | HTML sintético renderizado pelo Django e aberto em 320, 390, 768 e 1440 px para Visão geral, Despesas, Investimentos e formulário; sem overflow horizontal da página. Tema claro alternado e inspecionado em 390 px; modal visível nos quatro tamanhos. |

Os testes cobrem isolamento entre workspaces e perfis, grants e revogação, CSRF, limite concorrente, `NULL` versus zero, centavos, Reserva, cadastro sem movimentação bancária, vínculos históricos, migração e regressão de autenticação. Os comandos e saídas textuais estão em `C:/Users/Caio Tomaz/logs/2026-10-18_07-58-15.log`; imagens sintéticas de QA em `C:/Users/Caio Tomaz/.codex/visualizations/2026/10/18/01a14ea4-ec1d-7473-bfb9-90b6f8e6f785/alece-qa/`. O QA visual não equivale a teste E2E de um servidor autenticado no navegador.

## Limitações e riscos

1. **Alta antes de implantação:** dados legados com meta manual na Reserva bloqueiam `finance.0002`; executar preflight, decidir correção dos registros e testar em cópia do banco real. Não foi tocado banco persistente.
2. **Média:** dependências de produção ainda são faixas sem lock com hashes; resolução futura pode mudar. O scanner mede as versões resolvidas nesta data, não uma garantia permanente. Pipeline remoto do GitHub não foi executado nesta intervenção.
3. **Média:** grants são por perfil e não por módulo. Admin do núcleo acessa todos os perfis; comum requer grant. Interface de gestão de membros/grants e revisão de políticas mais finas ficam para outro sprint.
4. **Média:** não há fluxo completo de pagamento, estorno ou conciliação no Sprint 02. O resumo de pagamentos imprevisíveis usa batches existentes e não foi validado como extrato contábil em todos os cenários de estorno entre meses. Cadastros permanecem distintos de caixa confirmado.
5. **Baixa:** QA visual usou páginas sintéticas do Django e CDP, não jornada humana completa com servidor e banco persistente. O teste automatizado valida POST, erros de formulário e CSRF.

Não houve push, release, publicação de imagem, deploy, alteração de credenciais reais ou migração de banco persistente. Para operação, usar `RUNBOOK.md` e um backup de PostgreSQL verificado; os ZIPs da intervenção guardam somente o código.
