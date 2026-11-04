# Navegação, temas e URLs — ALECE

## URLs canônicas

- `/visao-geral/`
- `/despesas/`
- `/investimentos/`
- `/movimentacoes/`
- `/configuracoes/`

As URLs principais **não contêm IDs**. O backend resolve o núcleo ativo a
partir da sessão autenticada e valida a associação do usuário no PostgreSQL.
Se houver mais de um núcleo e não existir seleção, `/` apresenta a lista para
seleção. A rota `/selecionar-nucleo/<id>/` valida a associação antes de
registrar a escolha na sessão. URLs internas antigas sob `/finance/` são
mantidas temporariamente para não quebrar formulários e integrações.

Para usar um domínio personalizado, configure DNS, proxy reverso se desejado,
`ALECE_ALLOWED_HOSTS` e `ALECE_CSRF_TRUSTED_ORIGINS`. O ALECE não instala
proxy nem fornece certificados obrigatórios.

## Cadastro direto com seleção de perfil no formulário

- Os botões de criação de conta, despesa previsível/imprevisível,
  posição de investimento e transferência abrem **diretamente** o formulário.
- O campo "Perfil financeiro" é um `select` obrigatório dentro do próprio
  modal. Apresenta somente perfis ativos com permissão para a operação.
- A URL interna legada `finance:choose-profile-action` permanece válida,
  mas deixa de apresentar uma tela separada de escolha de perfil.
- Se houver um perfil explicitamente selecionado na navegação, ele é
  pré-selecionado no campo, sem restringir as alternativas autorizadas.
  O salvamento exige seleção explícita quando não houver preferência.
- Transferências atualizam as contas disponíveis após troca do perfil;
  a gravação segue com CSRF, autorização no serviço, idempotência e ledger.
- A preferência visual "Todos os perfis" não é alterada pelo cadastro.
  Os endpoints legados com `profile_id` continuam disponíveis.

## Tema por usuário

- Persistência principal: PostgreSQL, `core.UserProfile.theme`.
- Alternância: ícone Claro/Escuro na barra lateral ou navegação móvel.
- Gravação: POST autenticado `/preferencias/tema/`, protegido por CSRF.
- Cache do navegador: `localStorage`, separado pelo ID do usuário.
- Cookie `alece_theme`: lembrança visual para páginas não autenticadas;
  nunca é fonte de permissão ou acesso financeiro.
- Carregamento: o HTML já vem com `data-theme` resolvido no servidor; o CSS
  começa com o tema correto, evitando a troca visual ao renderizar.
- Outro dispositivo: o valor no banco é carregado independentemente do cache
  ou cookie do primeiro dispositivo.
- Erro ao gravar: a alternância é desfeita e o usuário recebe aviso.

O bloco "Aparência" não aparece em Configurações. Alterar senha e Recuperação
de acesso aparecem em Configurações → Conta e segurança. O ícone de informação
leva à página institucional do projeto.

## Execução e preservação dos dados

O `compose.yaml` usa `name: alece` conforme solicitado. **Antes de executar**
num host com instalações anteriores, inspecione `docker compose ls` e faça
backup dos volumes de dados. Alterar o nome da stack não migra dados da antiga
stack `alece-mvc`; pode criar um banco separado e também pode colidir com uma
stack já existente chamada `alece`. Não remova volumes automaticamente.

## Validações

Executadas no ambiente de empacotamento: compilação Python, validação de
sintaxe JS, Compose YAML, testes estruturais Python e um teste do manipulador
JS de tema com POST/CSRF/cópia local por usuário. Os testes de Django,
PostgreSQL e Docker requerem execução em host com dependências instaladas.
