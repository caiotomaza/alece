# ALECE — Auditoria funcional e estabilização incremental

**Data:** 27/10/2026  
**Base:** `ALECE_COMPLETO_Perfil_Principal_Minimo_Um_2026-10-27.zip`, SHA-256 conferido.  
**Resultado:** correções aplicadas ao código; **NÃO HOMOLOGADO PARA PRODUÇÃO CRÍTICA** até a execução da regressão Django/PostgreSQL isolada.  
**Escopo:** fluxos financeiros, isolamento entre perfis, autorização, importação, retornos de telas e idempotência.

## 1. Defeitos identificados e corrigidos

| Prioridade | Evidência no código original | Correção | Teste de regressão |
|---|---|---|---|
| P1 | `finance/transaction_views.py::_return_url` e `reverse_movement` retornavam às URLs com ID `/financas/nucleos/<id>/...` | Retornos públicos `/visao-geral/`, `/despesas/`, `/investimentos/` e `/movimentacoes/`, preservando somente o filtro de mês quando pertinente | `test_stabilization_public_flows.py` |
| P1 | `finance/views.py`: cancelamento de edição de perfil/renda levava à página legada do perfil | Cancelamento volta à gestão de perfis ou à Visão geral | `test_stabilization_public_flows.py` |
| P2 | `finance/reports_views.py::_reports_return_url` usava tela legada | Retorno público à Visão geral | Revisão estrutural; navegador pendente |
| P1 | `finance/import_views.py`: `int(account_id)`, `int(row_id)` e `Decimal(splits)` podiam falhar antes do tratamento de erro em POST manipulado | Validação central de identificadores/valores e mensagem compreensível; não usar exceção interna no texto público | `test_import_input_stability.py`, verificações isoladas do parser |
| P1 | `finance/import_views.py`: exceções inesperadas exibiam `str(exc)` ao usuário | Mensagem neutra; exceção detalhada mantida no logger local | Verificação estrutural; teste HTTP completo pendente |
| P0 | `finance/services/imports.py::stage_import/commit_import` verificava permissão, mas não bloqueava gravações em perfil arquivado | Bloqueio transacional da linha do perfil + rejeição de arquivado/excluído; impedido staging em conta arquivada | `test_import_input_stability.py`; concorrência PostgreSQL pendente |

## 2. Regras que foram mantidas sem refatoração

- Permissões de contas, despesas, investimentos, movimentações e perfis continuam validadas pelo backend.
- Identidade e saldo das contas continuam segregados por perfil. O cadastro de uma despesa não debita conta automaticamente.
- O ledger continua usando `transaction.atomic`, `select_for_update` e chave de idempotência única para confirmar operações e estornos.
- A seleção em `alece_selected_financial_profile_v1` é uma preferência de navegação. Os formulários usam seu `profile_id` autorizado como destino, sem alterar a sessão.
- Em `Todos os perfis`, criar ou importar exige escolher um perfil de destino permitido. Não existe destino financeiro “Todos”.
- Editar o perfil Principal é permitido; arquivar/excluir o último perfil ativo é bloqueado no serviço de perfis.
- Não houve mudanças de schema, migrations, identidades de dados nem substituição de componentes visuais.

## 3. Testes realmente executados neste ambiente

| Teste | Resultado | Limitação |
|---|---|---|
| SHA-256 do ZIP original | APROVADO | Arquivo da entrega anterior |
| Sintaxe/compilação Python (`src/controller`, `tests/`) | APROVADO | Não valida comportamento Django |
| `pytest` de cálculos e seleção de sessão | **9 aprovados**, 1 aviso | Aviso: `pytest-django` ausente neste ambiente |
| Execução isolada das funções de parsing por AST com dependências simuladas | **6 casos aprovados** (1 positivo, 5 negativos) | Não valida HTTP nem persistência |
| Estrutura do Compose de auditoria, sem portas, volumes e env_file de produção | APROVADO | Validação YAML estática, sem Docker |
| Django + PostgreSQL da suíte completa | **NÃO EXECUTADO** | Django, PostgreSQL e Docker indisponíveis aqui |
| Estresse concorrente e restauração de banco | **NÃO EXECUTADO** | Requer PostgreSQL isolado e observação das transações |
| Testes reais em navegador dos formulários | **NÃO EXECUTADO** | Requer servidor Django de teste |

Não alegamos conformidade funcional, segurança completa, cobertura integral ou disponibilidade 100% sem esses testes.

## 4. Testes adicionais incluídos para executar com PostgreSQL

- `tests/finance/test_stabilization_public_flows.py`: pagamento, transferência, resgate e estorno voltando às telas públicas; não alteração de sessão; replay idempotente; usuário sem permissão negado; retorno de cancelamento.
- `tests/imports/test_import_input_stability.py`: rejeição de IDs inválidos, `NaN`, infinito, quantias não positivas, período incorreto, tentativa de upload malformado e staging em perfil arquivado.

### Stack Docker de teste isolada

Foram adicionados `compose.audit.yaml`, `docker/Dockerfile.audit` e `scripts/Executar-Testes-Isolados.ps1`. A stack de teste:

- usa `postgres:16-bookworm` numa rede Docker específica **sem portas publicadas**;
- não utiliza `app_pgdata`, `app_secrets`, tokens de IA, volumes de produção ou containers com nomes fixos;
- usa credenciais literais **somente de testes sintéticos**; nunca as credenciais de `.env`;
- não monta diretórios do projeto como volume na base de dados;
- roda Django 5.2 e pytest usando o lock de desenvolvimento;
- não apaga logs nem backups. Containers de teste ficam disponíveis para inspeção após rodar.

Em Windows/PowerShell, após verificar que o Docker Desktop funciona, na pasta ALECE:

```powershell
.\scripts\Executar-Testes-Isolados.ps1
```

O script cria um único log no HOME do usuário: `%USERPROFILE%\logs\YYYY-MM-DD_HH-MM-SS.log`.

**Gate de liberação:** só implantar depois que o pytest isolado, teste de migrations, transações, estornos e autorização tiverem passado. Uma falha bloqueia a liberação.

## 5. Implantação e rollback

1. Preserve o ZIP original. Faça backup real e consistente do PostgreSQL, `.env`, segredos e volumes necessários, incluindo SHA-256 de cada artefato.
2. Execute a stack de regressão isolada e analise os resultados; não aponte esses testes para o banco de produção.
3. Extraia o **ZIP completo** diretamente na pasta existente do ALECE, mantendo o `.env` personalizado do operador. Os arquivos têm estrutura raiz, sem subpasta extra.
4. Verifique o diff. Nenhuma migration nova foi criada nesta atualização.
5. Após homologação, atualize **somente** o serviço web, preservando o banco e todos os volumes. Não use `docker compose down -v`.
6. Valide `manage.py check`, `/saude/pronto/`, criação e edição de cadastros, pagamento, estorno, seleção de perfis, upload/commit e logs de erro.
7. Se houver regressão: volte ao ZIP original e reconstrua o web; como não há migration, o schema é o mesmo. Em caso de inconsistência de dados, interrompa as operações e execute restauração do backup previamente testada.

## 6. Pendências e riscos residuais

- **P0:** teste concorrente real de operações monetárias, backup/restauração e fechamento contábil no PostgreSQL isolado.
- **P0:** regressão funcional de CRUD e autorização completa em ambiente Django executável.
- **P1:** revisar todos os endpoints legados não alterados neste lote; manter rotas antigas para compatibilidade não equivale a garantir que toda navegação use os destinos novos.
- **P1:** revisar importações externas malformadas, concorrência com arquivamento, limites de tamanho e atomicidade da importação de histórico.
- **P2:** auditoria visual responsiva e de acessibilidade com navegador real.

**Fontes de referência:** documentação Django 5.2 sobre `transaction.atomic()`, `select_for_update()` e testes com `TransactionTestCase`; PostgreSQL 16 sobre isolamento de transações e bloqueios: 

- https://docs.djangoproject.com/en/5.2/topics/db/transactions/
- https://docs.djangoproject.com/en/5.2/ref/models/querysets/#select-for-update
- https://docs.djangoproject.com/en/5.2/topics/testing/tools/
- https://www.postgresql.org/docs/16/transaction-iso.html
