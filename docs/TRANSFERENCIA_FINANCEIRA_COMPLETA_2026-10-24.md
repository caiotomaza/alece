# ALECE — Relatórios técnicos e transferência financeira portável

## Escopo

Em **Configurações → Relatórios financeiros**, o administrador acessa uma tela
separada contendo panorama financeiro e as operações **Exportar dados financeiros**
e **Importar dados financeiros**.

O ZIP de exportação contém:

- `financeiro.json`: dados e relações financeiras em formato versionado `alece-financeiro` v1.
- `leitura_financeira.xlsx`: planilha de leitura com aba por entidade financeira.
- `manifesto.json`: SHA-256 do JSON e do XLSX e contagem por entidade.
- `LEIA_ME.txt`: finalidade dos arquivos.

A restauração utiliza o JSON validado; o XLSX não é formato de importação.

### Entidades incluídas (14)

1. FinancialProfile — perfis ativos, arquivados e históricos excluídos logicamente.
2. BankAccount — contas, saldos e saldos de abertura.
3. RecurringExpense — despesas previsíveis.
4. UnexpectedExpense — despesas imprevisíveis.
5. InvestmentPosition — investimentos e metas.
6. ReservePolicy — configuração da Reserva.
7. MonthlyExpense — despesas planejadas congeladas por mês.
8. MonthlyInvestmentPlan — planejamentos mensais de investimento.
9. TransactionBatch — movimentações, pagamentos, aplicações, transferências e estornos.
10. LedgerLeg — lançamentos nas contas.
11. JournalEntry — partidas contábeis.
12. ImportBatch — lotes de importações financeiras, inclusive os em revisão.
13. ImportRow — linhas de importação e análises associadas.
14. CategorizationRule — regras financeiras atuais de categorização.

**Nunca são exportados:** usuários, e-mails do cadastro, senhas, tokens,
segredos, permissões (`ProfileGrant`), núcleos/associações de usuários,
logs (`SystemLog`), eventos de auditoria, histórico/versionamento de regras
(`CategorizationRuleVersion`) e histórico operacional de exportações (`ReportExport`).

As referências antigas a usuários em transações, lotes ou regras são removidas;
ao importar, o proprietário técnico obrigatório passa a ser o administrador
que executa a importação. Isso não reconstitui autoria histórica anterior.

## Segurança e comportamento

- Somente administrador do espaço tem acesso às operações.
- Importação via `POST` protegido por CSRF, com confirmação escrita `IMPORTAR` e
  confirmação explícita do impacto das permissões concedidas no destino.
- ZIP até **25 MiB**, limite total descompactado de **65 MiB**, 100.000 registros.
- Tabelas e campos esperados são verificados; não são aceitos comandos/SQL
  arbitrários ou conteúdo inesperado.
- SHA-256 do JSON e da planilha validado antes de importar.
- Backup do estado financeiro do destino **antes** de qualquer gravação, validado
  com SHA-256; o arquivo é mantido em `$HOME/backups/` do usuário do serviço.
- No Docker, `/home/app/backups` passa a ser volume persistente `app_financial_backups`.
  Faça backups externos desse volume. Permissões de arquivo 0600.
- Importação aditiva em `transaction.atomic()`, com novos IDs financeiros e
  referências reconstituídas (inclusive estornos), sem sobrescrever existentes.
- Nomes de perfis/regras conflitantes recebem sufixo `(Importado N)`.
- Se já houver cinco perfis ativos, os perfis adicionais são importados arquivados.
- O ALECE **não importa permissões da origem**. Após a importação, cria direitos
  de edição para os **usuários já cadastrados no destino** nos perfis importados.
  O administrador deve revisar essas permissões em Configurações imediatamente.
- Não recupera identidades, senhas, sessões ou autorização antiga, mesmo
  quando os nomes de usuário coincidam.
- Dados financeiros podem conter informações pessoais em descrições ou extratos;
  trate o ZIP e o backup como confidenciais e armazene-os de forma segura.

## Implantação e rollback

1. Identifique a stack ALECE existente; preserve o `.env` instalado e os volumes.
2. Antes da atualização, faça dump PostgreSQL e backups dos volumes persistentes,
   com SHA-256 validado. Isso protege também contra erros de implantação.
3. Atualize o código do projeto inteiro. Não execute `docker compose down -v`.
4. Verifique `ALECE_LOG_VALIDACAO=true` no `.env` e `.env.example`.
5. Reconstrua o serviço web de modo controlado, sem remover o banco.
6. Valide as URLs: `/configuracoes/`, `Relatórios financeiros`, exportar ZIP,
   abrir o XLSX, verificar manifesto e importar num **ambiente de teste**.
7. Rode o teste Django: `python manage.py test tests.test_financial_transfer`.
8. Para voltar à versão anterior, restaure o código anterior e os volumes/dump
   compatíveis; não apague os backups. Para reverter uma importação concluída,
   restaure o backup financeiro pré-importação em uma base isolada e siga
   processo administrativo de substituição do ambiente de destino. A importação
   aditiva não fornece botão de desfazer após o COMMIT.

**Importante:** exportação financeira **não substitui** backup completo do PostgreSQL.
O escopo limitado é intencional e não carrega autenticação, permissões nem auditoria.
