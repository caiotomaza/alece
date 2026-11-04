# Validação — POST incorreto em modais de configuração

Data: 2026-10-28. Base: ZIP completo de confirmação de exclusão de perfil, com SHA-256 validado.

## Evidência de regressão antes/depois

- Com o JavaScript original e o novo caso Playwright, o teste reprovou como esperado: recebida a URL `[object HTMLInputElement]`, em vez de `about:blank?salvar`. Isso reproduz a causa registrada nos logs do usuário.
- Depois da correção, `ALECE_TEST_ISOLATED=1 ALECE_DB_NAME=test_alece_unit ALECE_DB_HOST=localhost pytest -q tests/modals/test_modals_browser.py tests/configuration/test_profile_delete_keyword_contract_no_django.py`: **24 testes aprovados**, 1 aviso de configuração (`pytest-django` ausente).
- `node --check src/view/static/finance/alece.js`: aprovado.
- Teste de sintaxe Python do módulo de testes: aprovado.
- ZIP e hashes devem ser verificados após o empacotamento.

## Ambiente e limitações

- Testes DOM executados no Chromium através do Playwright com backend HTTP simulado.
- Django e PostgreSQL não estavam disponíveis para execução integrada neste ambiente.
- Não foram alterados banco, migrations, configurações persistentes, arquivos `.env` ou políticas de segurança.
- Antes de produção, verificar com instância isolada os POSTs de edição e exclusão, permissões, mensagens e persistência financeira.

## Principais riscos residuais

1. Implantar apenas reconstruindo o container, sem atualizar `alece.js` no código de origem, manterá o erro antigo.
2. Sobrescrever `.env` produtivo pode alterar configurações ou segredos; preservar o existente.
3. Execução integrada e navegadores adicionais não foram testados nesta rodada.
4. O warning existente `(urls.W005)` de namespace admin duplicado não foi corrigido nesta intervenção restrita.
