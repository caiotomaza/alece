# ALECE — correção de espaçamento entre seções (23/10/2026)

## Escopo

- Visão geral: `Saldo` e `Resumo` voltam a ter **22 px** de separação vertical no desktop e **16 px** no celular. O título `Resumo` e o botão editar permanecem **dentro** do cartão.
- Investimentos: a seção `Metas` recebe o mesmo respiro vertical em relação aos cartões anteriores.
- Configurações: `Usuários`, `Perfis`, `API`, `Logs` e `Relatórios` passam a ter um **recuo interno do painel** de **22 px no desktop** e **15 px no celular**. Tabelas têm sua própria borda arredondada, com colunas recuadas da borda.
- Preservados: bento grid de Configurações, controles, permissões, rotas, tema, comportamento mobile e modelos Django.

## Causa do problema

O CSS `src/view/static/finance/alece.css` tinha regras de padding para seções, mas a folha carregada **depois**, `src/view/static/finance/alece_ui_consistency.css`, aplicava `padding:0` em `.alece-settings .settings-admin-section`. Como os títulos `Resumo` e `Metas` foram transferidos para dentro dos cartões, as margens anteriormente presentes nos títulos externos deixaram de separar os blocos. A intervenção modifica a definição responsável no CSS de maior precedência e restabelece o ritmo vertical.

## Verificações

- Teste com Chromium utilizando **HTML de prévia com os seletores reais e os dois arquivos CSS reais**, nos temas claro/escuro e larguras **320, 390, 768, 1280 e 1500 px**.
- Margem entre Saldo e Resumo, entre Resumo e cartões subsequentes, entre cartões de investimentos e Metas e recuos laterais das três primeiras tabelas verificados por medidas de DOM.
- Nenhum transbordamento horizontal da página nos cenários testados.
- `AST` dos arquivos Python, sintaxe JavaScript, CSS e integridade do ZIP verificados.
- **Não foi executada a aplicação Django/PostgreSQL em Docker** neste ambiente; os testes acima não substituem testes de ponta a ponta em produção.

## Aplicação sem perda de dados

1. Faça backup do seu `.env`, dos arquivos personalizados, dos volumes persistentes (`app_pgdata`, `app_media`, `app_ai_tokens`, `app_secrets`) e um dump PostgreSQL. Calcule e valide SHA-256 antes de substituir a instalação.
2. Extraia o **ZIP completo** em um diretório separado. Nunca execute `docker compose down -v`.
3. Preserve seu `.env` atual se contiver configurações locais; o ZIP inclui um `.env` padrão com `ALECE_LOG_VALIDACAO=true`, que deve ser mantido ao atualizar.
4. Transfira os arquivos do projeto sem sobrescrever dados persistentes. Na raiz da instalação, execute `docker compose up -d --build web` (PowerShell ou shell com Docker Compose habilitado).
5. Abra `/visao-geral/`, `/investimentos/` e `/configuracoes/` em temas claro/escuro, no celular e desktop. Confira o console e os logs em `src/logs/`.
6. Se houver regressão, restaure os arquivos anteriores a partir do backup validado e reconstrua o serviço web. Não faça rollback destrutivo de volumes. Como não há alteração de banco/migração neste pacote, o rollback do código é direto.

Arquivos `.env` do projeto **não contêm senhas ou tokens de produção**; segredos operacionais são mantidos em volumes do Docker. O ZIP completo não contém o banco de dados da sua instalação.
