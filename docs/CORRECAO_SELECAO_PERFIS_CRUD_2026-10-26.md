# ALECE — Seleção de perfis em navegação e CRUD

## Objetivo

Corrigir perdas da seleção de perfil após criação/edição e manter as ações de cadastro quando a visão está em **Todos os perfis**, exigindo um destino explícito.

## Regras implementadas

- A seleção exibida no menu é uma **preferência de leitura** salva na sessão autenticada; só a navegação explícita `?profiles=<id>` ou `?profiles=all` a altera. Formulários de CRUD e seus redirects não modificam essa preferência.
- O menu mostra **Todos os perfis** mesmo que exista só um perfil e a preferência esteja vazia.
- Páginas de edição avulsas agora carregam a seleção vigente a partir dos perfis autorizados, não do registro que está sendo alterado.
- Após salvar **conta/renda**, a navegação retorna à **Visão geral**; após salvar **despesas**, a **Despesas**; após salvar **investimento/reserva**, a **Investimentos**.
- Os botões de adição de conta, despesas, investimento, transferência e edição de renda continuam disponíveis na visão agregada quando há pelo menos um perfil com autorização para a respectiva ação.
- Quando **Todos os perfis** está selecionado, a ação abre um seletor modal de perfil antes do formulário. Apenas perfis **ativos**, não excluídos e autorizados para aquele módulo podem ser escolhidos. Selecionar um destino não troca a preferência do menu.
- A importação de extratos na visão agregada exige a escolha explícita do perfil; não usa automaticamente o primeiro perfil autorizado. Sem JavaScript, são exibidos links para os formulários por perfil.
- A edição de uma linha existente continua usando o perfil do próprio registro, sob o controle de permissão do servidor.
- Nenhum dado é movimentado automaticamente ao escolher um perfil; os formulários e transações existentes continuam separados.

## Arquivos principais

- `src/controller/apps/finance/views.py` — opções e autorização para o modal, estado da sessão, redirects.
- `src/controller/apps/finance/urls.py` — rota `nucleos/<id>/escolher-perfil/<operation>/`.
- `src/view/templates/finance/choose_profile.html` — seleção responsiva.
- `src/view/templates/finance/workspace_page.html` — botões quando Todos.
- `src/view/templates/finance/_movement_import.html` — perfil obrigatório na importação.
- `src/controller/apps/finance/templatetags/alece_navigation.py` — menu em formulários diretos.
- `src/view/templates/finance/base.html` — navegação consistente.
- `src/view/static/finance/alece.js` — fluxo de modais e seleção de perfil para importação.
- `tests/finance/test_all_profiles_actions.py` — testes de integração Django/PostgreSQL.

## Verificação da instalação

1. Selecione um perfil na navegação. Salve uma despesa. Confira o perfil selecionado ao retornar a Despesas.
2. Selecione **Todos os perfis**. Abra o `+` em Despesas. Escolha o destino no primeiro modal; o segundo modal deve ser o cadastro de despesa.
3. Salve o cadastro; confirme que o menu permanece em **Todos os perfis** e que o registro aparece no perfil de destino.
4. Repita nos módulos Visão geral (conta e renda), Investimentos e Movimentações (transferência/importação).
5. Use usuário comum com permissões somente em um perfil: o seletor não pode mostrar outros perfis.
6. Teste a mesma sequência em desktop e celular, tema claro e escuro.

## Evidência e limites

Foram realizados testes estáticos e testes sem Django nesta entrega. Os testes Django/PostgreSQL não foram executados neste ambiente. Nenhuma migration foi criada nem o banco foi alterado aqui.

## Implantação e reversão

Antes de substituir a aplicação, gere **backup consistente do PostgreSQL, volumes e `.env`**, calcule SHA-256 e confirme a integridade. Faça também cópia da versão da aplicação anterior. Extraia o ZIP completo diretamente na pasta ALECE e reconstrua apenas o serviço web. Reversão: restaure a versão anterior da aplicação dos backups validados e mantenha o banco/volumes (não há migration nesta correção). Não use `docker compose down -v`.
