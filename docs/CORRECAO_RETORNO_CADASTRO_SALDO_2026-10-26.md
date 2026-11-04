# Retorno do cadastro de conta / saldo à Visão geral

## Sintoma
Após cadastrar saldo/conta, o navegador abre a página legada `/financas/perfis/<id>/` em vez de `/visao-geral/`.

## Diagnóstico
No ZIP de origem, o `account_create` já executava `redirect("visao-geral")`, então a captura sugere que o container em execução ainda pode estar rodando um build anterior. Esta versão explicita `reverse("visao-geral")`, uniformiza o cancelamento dos formulários de conta para a rota pública e inclui testes de regressão de redirecionamento, persistência de seleção e validação.

## Resultado esperado
- Criar uma conta/saldo: `POST` concluído -> HTTP 302 -> `/visao-geral/`.
- Cancelar o cadastro: `/visao-geral/`.
- O perfil financeiro escolhido na barra lateral continua igual.
- `Todos os perfis` não muda para um perfil específico após cadastro.
- Erro de validação mantém o formulário com os erros; sem dados gravados.

## Implantação Docker Desktop
1. Faça backup completo do banco, volumes e diretório do projeto; gere e confira SHA-256 antes de substituir.
2. Extraia os arquivos deste ZIP diretamente na raiz da instalação `alece/` e substitua os existentes, preservando o `.env` próprio.
3. Recrie **apenas** o serviço web (com Docker Compose disponível): `docker compose up -d --build --force-recreate --no-deps web`.
4. Verifique com `docker compose logs --tail 100 web` e teste a inclusão de uma conta; confirme a URL final.
5. Não use `docker compose down -v`.

## Validação de integração em banco isolado
`python manage.py test tests.finance.test_account_return_overview`

## Rollback
Restaure o backup com SHA-256 verificado dos arquivos alterados (`views.py`, `account_form.html`), ou restaure a cópia anterior completa do projeto, e recrie apenas o serviço web. Os registros criados após o backup devem ser reconciliados separadamente; restaurar código não desfaz alterações financeiras no PostgreSQL.
