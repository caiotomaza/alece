# ALECE — Confirmação de exclusão de perfil com palavra fixa

Data: 2026-10-28. Escopo restrito à exclusão lógica de perfis financeiros.

## Comportamento anterior

A exclusão exigia digitar o nome exato do perfil financeiro (`confirm_profile_name`).

## Comportamento atualizado

- A interface orienta o administrador a digitar **CONFIRMAR**, em maiúsculas, no campo `confirm_deletion`.
- A validação HTML (`required`, `pattern`, `maxlength`) fornece feedback antecipado, mas **não é a proteção de segurança**: o serviço Django verifica `confirmation == "CONFIRMAR"`, rejeitando qualquer outro texto ou requisição que use apenas o campo antigo.
- O botão de exclusão continua sendo uma ação explícita separada dos formulários de dados e permissões, com confirmação adicional na interface, sem exclusão automática.
- Permanecem a verificação de administrador, proteção do último perfil ativo, transação/locks, exclusão lógica, revogação de permissões e preservação de histórico/auditoria.
- Sem alteração de schema, migrations, JavaScript, CSS, `.env`, PostgreSQL ou volumes.

## Arquivos modificados

1. `src/controller/apps/finance/services/profiles.py` — validação da palavra no servidor.
2. `src/controller/apps/finance/views.py` — novo campo POST.
3. `src/view/templates/finance/profile_manage.html` — rótulo e campo de confirmação.
4. `tests/configuration/test_profile_soft_deletion.py` — casos HTTP positivos/negativos.
5. `tests/configuration/test_minimum_active_profile.py` — atualização do contrato de testes existente.

Adicionado `tests/configuration/test_profile_delete_keyword_contract_no_django.py` para verificar a conexão básica entre interface, view e serviço mesmo em ambiente sem Django.

## Validação e riscos residuais

Consulte `docs/alteracoes/2026-10-28_validacao_confirmar.md` para os resultados executados. Os testes de integração Django com PostgreSQL são obrigatórios antes da implantação. A confirmação textual é uma salvaguarda de UX, não substitui autenticação/autorização nem backups.

## Atualização

1. Realizar backup verificável dos arquivos da instalação e preservar o `.env` produtivo e os dados persistidos do PostgreSQL. Registrar SHA-256 do backup.
2. Validar o SHA-256 do ZIP desta entrega e extrair os arquivos diretamente na raiz da pasta `alece`.
3. Validar o template e a rota de edição de perfil; aplicar atualização normal da aplicação conforme o processo existente, sem reiniciar banco desnecessariamente.
4. Testar com dois perfis ativos: `CONFIRMAR` aceita a exclusão de um deles, textos incorretos não aceitam; usuário não administrador é bloqueado; último perfil ativo é protegido.
5. Conferir logs de aplicação e verificar que as informações financeiras e permissões foram preservadas.

## Rollback

Restaurar o backup integral anterior com SHA-256 validado, repor os arquivos estáticos quando necessário e executar a regressão. Não há migrations a reverter. **Se alguma exclusão lógica já tiver ocorrido após a instalação, a restauração do código não desfaz essa exclusão; a recuperação de dados exigirá procedimento próprio, respaldado pelo backup do PostgreSQL e pelo histórico de auditoria.** Não restaurar o banco automaticamente em produção.
