# Permissões por perfil: ações em massa sincronizadas

Ao marcar **Visualizar**, qualquer módulo em Sem acesso passa a Visualização sem reduzir acessos de Edição. Marcar **Editar** define os cinco módulos como Edição e marca Visualizar. Desmarcar **Editar** reduz os módulos que estavam em Edição para Visualização. Desmarcar **Visualizar** define todos como Sem acesso.

Alterações individuais nos dropdowns atualizam os indicadores globais. Um indicador parcialmente selecionado significa que somente alguns módulos têm aquele direito. O acesso real é determinado pelo módulo, com permissões aplicadas pelo servidor, e apenas é persistido ao clicar em **Salvar permissões**.

`core:grant-management` valida os cinco níveis antes da escrita; calcula `can_view`/`can_edit` a partir dos níveis recebidos; rejeita valores inválidos com HTTP 400; aplica todas as mudanças na mesma transação. Usuários comuns não podem administrar grants. Não há migração.

## Testar

1. Em Configurações → Usuários, abra o lápis de um usuário comum e expanda Permissões em perfis.
2. Marque Editar: os cinco dropdowns devem mudar para Edição.
3. Desmarque Editar: todos devem ir a Visualização.
4. Desmarque Visualizar: todos devem ir a Sem acesso.
5. Mude um módulo para Edição: Editar deve ficar no estado parcial; altere os demais para Edição e observe o indicador completo.
6. Salve e abra novamente. Confira que os módulos e os indicadores refletem os valores persistidos.

## Recuperação e segurança

Preserve a instalação atual antes da atualização: backup do código, `.env`, volumes e dump do PostgreSQL com SHA-256 validado. Nunca execute `docker compose down -v`. O backup da intervenção realizada sobre a cópia nesta entrega fica em `HOME/backups/` com hash; o log correspondente está em `HOME/logs/`. Caso precise reverter, restaure o ZIP anterior integral e mantenha o banco/volumes sem alteração.
