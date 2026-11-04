# ALECE — Ajuste da gestão de contas e saldos (29/10/2026)

## Escopo

A tela `/financas/perfis/<id>/` foi reorganizada para listar contas bancárias e dinheiro físico de um perfil financeiro. As colunas são **Nome**, **Perfil financeiro** e **Quantia**, com o tipo da conta indicado junto ao nome e a ação de editar na mesma linha. A renda e as permissões foram mantidas em uma seção secundária, sem misturar renda e saldo.

O novo CSS `src/view/static/finance/alece_profile_balances.css` utiliza exclusivamente os tokens do Design System ALECE. Há adaptação de tabela para cartões em telas estreitas, estados vazio, saldo desconhecido e perfil arquivado, além de foco de teclado e temas Claro/Escuro. Não foram adicionados gradientes ou dependências.

## Contratos funcionais preservados

- Contas pertencem a um único perfil e núcleo; somente o módulo `accounts` autoriza visualizar e editar. Usuários sem o direito de ver contas recebem estado de acesso restrito, sem valores ou nomes de contas.
- Administradores do núcleo podem gerir seus perfis; usuários comuns dependem de concessões já existentes. Ações de edição continuam protegidas no backend por `editable_profile()` e `save_record()`.
- Saldo `NULL` continua desconhecido, diferente de `0.00`. O cadastro de saldo não gera movimentação nem renda. Registros com histórico financeiro vinculado preservam a regra de conciliação.
- Links de nova conta e edição abertos pela tela de saldos incluem `?return=profile`; nesse contexto o formulário retorna à página do perfil. Para acessos antigos sem o parâmetro, o destino de retorno continua sendo a Visão geral. O parâmetro é uma opção fechada, não uma URL fornecida pelo cliente.
- Rotas, modelos, migrations, serviços financeiros, formatos de dados, CSRF e política de permissões não foram alterados.

## Arquivos alterados

- `src/view/templates/finance/profile_detail.html`
- `src/view/static/finance/alece_profile_balances.css` (novo)
- `src/view/static/finance/alece.js`
- `src/controller/apps/finance/views.py`
- `tests/finance/test_profile_balance_management.py` (novo)
- `tests/ui/test_profile_balances_structure.py` (novo)

## Validação e limites

- A compilação Python do controller e dos novos testes passou; `node --check` do JavaScript passou.
- Sete testes estruturais `unittest` passaram (6 anteriores do UI + 1 novo).
- A prévia sintética em Chromium passou sem overflow global em 320, 390, 768, 1280 e 1920 px, nos temas Claro/Escuro. O foco do botão foi detectado como visível; capturas foram revisadas visualmente. Essa prévia não é a tela Django autenticada.
- Testes Django/PostgreSQL, integração HTTP/POST, rotas autenticadas, permissões reais, regressão completa e acessibilidade assistiva **não foram executados**, pois o ambiente de empacotamento não possui Django/PostgreSQL. Testes específicos de retorno e ACL foram adicionados para a suíte isolada do projeto.

Para homologar, executar os gates de `AGENTS.md` com PostgreSQL de teste efêmero, checar modais, tabulação e POSTs reais com administrador, leitor, editor, perfil arquivado e perfil sem direito ao módulo de contas. Não usar base produtiva para testes. Antes de atualização em instalação existente, seguir backup/rollback do `RUNBOOK.md`; nenhum volume, segredo ou banco foi modificado nesta revisão.
