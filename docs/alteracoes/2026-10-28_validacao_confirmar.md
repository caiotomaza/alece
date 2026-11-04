# Relatório de validação — Exclusão de perfil com CONFIRMAR

**Data:** 2026-10-28

**Base:** `ALECE_COMPLETO_PERFORMANCE_USABILIDADE_2026-10-27.zip`

**Integridade da base:** SHA-256 `cabc4499c7477bab371b2cde878678557cc8fbe9b698f6591d0955a36879ff2f`, idêntico ao arquivo `.sha256` recebido.

## Resultado efetivamente executado

| Verificação | Resultado | Limitação |
| --- | --- | --- |
| Backup completo da versão anterior e checksum | Aprovado | Cópia preservada em `HOME/backups/` com `.sha256` |
| Compilação dos módulos Python alterados | Aprovado | Apenas análise sintática |
| Testes sem Django (contratos, segurança estática, arquitetura e Design System) | **20 aprovados**, 0 falhas | Não executam serviço Django nem banco |
| Integração da exclusão (POST, autorização e exclusão lógica) | **Não executado** | Django, pytest-django e PostgreSQL indisponíveis neste ambiente |
| Testes reais de navegador/modal | **Não executado** | Chromium executável indisponível neste ambiente |
| Migrations | **Nenhuma nova** | Não houve alterações de modelos |
| Regressão financeira integrada | **Não executada** | Depende do ambiente Django/PostgreSQL isolado |

A execução de pytest apresentou 1 aviso (`DJANGO_SETTINGS_MODULE` desconhecido) devido à ausência de `pytest-django`; não corresponde a aprovação de integração. O código atualizado possui novos testes Django para os casos positivo, palavra incorreta, palavra em minúsculas, campo legado, ausência de texto e visualização do formulário, mas **esses testes permanecem pendentes de execução**.

## Comportamento esperado a confirmar na homologação

1. Administrador + dois perfis ativos + `confirm_deletion=CONFIRMAR`: exclusão lógica concluída, histórico preservado e permissões revogadas.
2. Palavra incorreta (`Principal`, `Teste`, `confirmar` ou vazio), inclusive via requisição direta: perfil não excluído.
3. Campo antigo `confirm_profile_name` sem o campo novo: perfil não excluído.
4. Usuário comum: acesso bloqueado, mesmo digitando `CONFIRMAR`.
5. Último perfil ativo: exclusão bloqueada mesmo com `CONFIRMAR`.
6. Formulário: rótulo explícito, validação HTML e confirmação adicional antes do POST.

## Riscos residuais

- Não foi homologada nesta execução a compatibilidade com o banco PostgreSQL e fluxos autenticados reais. **Não liberar para produção sem esses testes**.
- A confirmação por palavra fixa reduz erros acidentais, mas não é fator de autenticação. Permanecem indispensáveis as permissões de backend e confirmação consciente do usuário.
- Como a exclusão é lógica, rollback apenas do código não reverte exclusões já executadas.

## Fontes técnicas

- Django 5.2: Forms / POST / validação: https://docs.djangoproject.com/en/5.2/topics/forms/
- Django 5.2: CSRF: https://docs.djangoproject.com/en/5.2/howto/csrf/
