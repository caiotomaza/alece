# ALECE — correção de POST 404 no modal de gestão de perfis

## Evidência observada

Os logs recebidos mostram `POST /configuracoes/perfis/[object HTMLInputElement]` com HTTP 404, enquanto a inicialização da aplicação e PostgreSQL é saudável.

## Causa raiz

O template `profile_manage.html` contém `<input type="hidden" name="action" value="profile">` (e ações similares). Conforme as regras de acesso a elementos nomeados no DOM, esse campo pode mascarar a propriedade nativa `HTMLFormElement.action`. O frontend em `alece.js` utilizava `postingForm.action`, recebendo o elemento HTML, depois convertido em `[object HTMLInputElement]`. A operação nem chegava à rota Django válida.

## Correção de escopo mínimo

- Em `src/view/static/finance/alece.js`, o endereço de submissão é lido de `postingForm.getAttribute('action')`, com fallback na URL atual.
- A ação preservada ao renderizar resposta do servidor é obtida do atributo real.
- A atribuição de endereço a formulários retornados por AJAX usa `setAttribute('action', ...)` para evitar conflitos de nomes.
- Não houve mudanças no backend financeiro, modelos, permissões, migrations, rota, arquivos `.env`, banco ou volumes.
- Regressão Playwright com formulário possuindo `name="action"` foi adicionada.

## Implantação e validação

1. Criar backup SHA-256 dos arquivos afetados e preservar `.env` produtivo.
2. Substituir o projeto usando o ZIP integral, evitando sobrescrever `.env` produtivo.
3. Executar a reconstrução de `web` (`docker compose build web`) e recriar apenas `web` (`docker compose up -d --no-deps --force-recreate web`), sem `down`, `prune` ou exclusão de volumes. Os estáticos WhiteNoise com hashes são recriados durante o build.
4. Confirmar `docker compose ps`, healthcheck e verificar o JavaScript servido. Se necessário, atualizar a aba com `Ctrl+F5`.
5. Testar salvar o nome de um perfil, editar permissões e a exclusão com `CONFIRMAR` **em banco de testes antes de produção**. Inspecionar se não há novos POSTs com `[object HTMLInputElement]`.

## Rollback

- Restaurar o arquivo `src/view/static/finance/alece.js` do backup validado ou restaurar o ZIP anterior inteiro. Reconstruir somente `web`.
- Os dados PostgreSQL não são modificados pela atualização do JS. Não restaurar automaticamente o banco.
- Reavaliar operações realmente confirmadas pelo usuário após a atualização, antes de qualquer restauração de dados.

## Limitações

O teste Playwright cobre o comportamento DOM e a requisição com backend simulado. Sem Django e PostgreSQL disponíveis nesta sessão, a regressão integrada permanece pendente. Limpar cache por si só não corrige a causa raiz.
