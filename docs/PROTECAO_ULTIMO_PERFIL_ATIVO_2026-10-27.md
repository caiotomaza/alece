# ALECE — integridade do último perfil financeiro ativo

Data: 2026-10-27  
Origem: `ALECE_COMPLETO_Gestao_Administrativa_Em_Paginas_2026-10-27.zip`.

## Regras implementadas

- O nome **Principal** não possui bloqueio especial. Administradores podem editar
  nome, emoji e renda mensal inclusive se for o único perfil ativo.
- Deve existir **ao menos um perfil ativo por espaço financeiro**; um perfil
  arquivado ou excluído logicamente não conta como ativo.
- Excluir ou arquivar o último perfil ativo é recusado **pelo serviço Django**
  mesmo se alguém enviar POST diretamente, burlando o botão desabilitado.
- Se outro perfil ativo existir, o Principal pode ser arquivado ou excluído
  logicamente. A exclusão preserva lançamentos, vínculos financeiros e auditoria,
  mas revoga concessões e não é revertível pela interface.
- O perfil é identificado por ID e espaço, não pelo texto do nome.
- O backend protege as operações concorrentes usando transação e lock na linha
  de `Workspace`, compartilhado pelas operações de criação, arquivamento e exclusão.
- Reativar continua respeitando o máximo de cinco perfis ativos.
- Com um único perfil ativo, o modal comunica o bloqueio e mantém a ação
  **Salvar perfil** habilitada.
- A confirmação textual da exclusão é mantida, sem `confirm()` nativo duplicado.
- Em falha HTTP, o modal mantém o formulário aberto e mostra o status quando
  disponível. Detalhes de exceção não são enviados ao navegador.

## Arquivos alterados

- `src/controller/apps/finance/services/profiles.py`
- `src/controller/apps/finance/views.py`
- `src/view/templates/finance/profile_manage.html`
- `src/view/static/finance/alece.css`
- `src/view/static/finance/alece.js`
- `tests/configuration/test_minimum_active_profile.py` (novo)
- Ajustes de testes antigos em `tests/configuration/` e `tests/finance/`.

## Implantação segura

1. Pare alterações de usuários durante a atualização.
2. Faça backup consistente do PostgreSQL e volumes, valide SHA-256, preserve
   o `.env` existente. Uma cópia da pasta de código, sozinha, não protege dados.
3. Extraia os arquivos deste ZIP **na raiz da instalação ALECE**, substituindo
   os existentes. Não há pasta `alece/` adicional.
4. Em instalação Docker Compose, reconstrua e recrie **somente** o serviço `web`.
   Não execute `docker compose down -v`.
5. Consulte os logs em `src/logs/` (com `ALECE_LOG_VALIDACAO=true`), revise
   o log de startup e o status de `/saude/pronto/`.
6. Execute os testes Django em **banco PostgreSQL isolado** e valide na interface:
   editar nome e renda do único perfil, negar sua exclusão/arquivamento,
   criar um segundo perfil e então excluir ou arquivar o primeiro.

## Reversão

Se a validação falhar, reimplante a versão-base completa preservada e reconstrua
somente `web`. O backup focado em `HOME/backups/` também contém os arquivos
originais alterados, com `<backup>.sha256`. Como não há migração nova, a reversão
não exige alterar o esquema. Se operações reais ocorreram após a implantação,
**não restaure um dump antigo sobre esses novos dados** sem análise prévia.

## Escopo e limitações

A verificação sintática e estrutural não substitui Django/PostgreSQL. Não foi
possível reproduzir o erro HTTP 500 da instalação do usuário sem os respectivos
logs da requisição e um banco equivalente. Se ele persistir, o status exibido
no modal e os logs do servidor ajudam a identificar a causa exata. O bloqueio
cobre as operações de gerenciamento suportadas; alterações manuais diretas
no banco por administrador externo não são tratadas nesta revisão.
