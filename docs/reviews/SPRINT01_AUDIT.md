# Auditoria do Sprint 01 — 2026-10-18

## Decisão: GATE A APROVADO

Sem bloqueadores críticos/altos remanescentes no escopo auditado. Evidência sequencial final: **69 coletados, 69 aprovados, 0 falhas, 0 ignorados**, além de 8 subtestes. PostgreSQL 16 real em tmpfs, rede Docker interna sem porta publicada; Python 3.12.15, Django 5.2.18. Banco/containers persistentes existentes não foram acessados. Aprovação autoriza apenas o desenvolvimento local do Sprint 02, não produção.

## Base e contagem

Commit inicial `e9e36a6e05a86626f3ac2ee77e9178fcc7676ecb` contém Sprint 01: 40 testes, sendo 26 métodos em `tests/test_auth.py`. A alegação de 27 testes novos não encontra suporte nesse arquivo; não confundir contagem declarada com verificação de comportamento. Um dos 26 era apenas docstring + `pass`; agora verifica HTTP 403 de perfil sem grant. O snapshot de entrada também continha o fluxo de perfis/contas não commitado: 12 testes adicionais, total 52, efetivamente aprovados em PostgreSQL antes das correções. A auditoria acrescentou 14 testes de autenticação e 3 de permissões/concorrência, total 69.

## Achados

| Achado / gravidade | Evidência e localização original | Correção | Teste / resultado | Risco residual |
|---|---|---|---|---|
| Crítica: tomada de conta por emissão anônima de recuperação | `apps/core/auth_views.py:recovery_code_request_view` emitia código conhecendo somente username | Endpoint antigo informativo; emissão autenticada com senha atual; códigos legados recusados por versão | Emissão anônima negada, senha atual obrigatória, legado recusado: passou | Atualizações exigem nova emissão pelos proprietários; não houve alteração de credenciais reais |
| Alta: replay concorrente de recuperação | Leitura/consumo sem lock comum | `auth_services.py` trava usuário em emissão e consumo, atomiza senha + invalidação | Dois resgates concorrentes: exatamente um sucesso, PostgreSQL | Requer PostgreSQL e migration aplicada |
| Alta: tentativas ilimitadas e reset sem validadores | Endpoints auth e admin sem quota, `set_password` direto | Buckets PostgreSQL por identificador HMAC; 10/conta e 60/peer a cada 15min, compartilhados por workers; SetPasswordForm | Quotas públicas/admin, concorrência, reabertura, validação e sessões: passou | NAT/proxy compartilha limite de peer; sucesso também consome quota, possível bloqueio temporário |
| Média: open redirect | `next` retornado diretamente | Validação host/esquema e fallback home | URLs externas recusadas, interna aceita: passou | TLS/proxy devem ser configurados pelo operador |
| Média: enumeração na recuperação | Mensagens diferentes para inexistente/sem código | Mensagem genérica para recuperação inválida | Usuários inexistentes/inativos: passou | Não há garantia formal de tempo constante de toda a resposta |
| Média: divergência política admin | Helpers exigiam grants para admin, contrariando SPEC RF-058 | Admin só no próprio workspace; comum precisa grant; edit implica view | Isolamento HTTP e revogação imediata: passou | Grants têm granularidade por perfil, não por módulo (evolução futura) |
| Média: escrita financeira pelo Admin | Admin podia criar perfis sem serviço/limite e alterar ledger/saldos | Financeiro somente leitura no Admin; workspace/memberships/grants para operador | POST admin negado: passou | SQL/ORM internos são fronteira confiável; não há RLS |
| Média: grant cruzado | Relação permitia membership de outro workspace | Query exige mesmo workspace; clean rejeita concessão cruzada | Manipulação de identificadores e grant inválido: passou | FK composta/RLS não implementados; filtros e serviços são obrigatórios |
| Baixa: hash comparado diretamente/cache | `UserProfile` e respostas de recuperação | Comparação constante, never_cache, sensitive_post_parameters | Replay/rotação/invalidação verificados | Logs de proxy também devem excluir corpos e secrets |
| Baixa: script manual inseguro | `test_recovery.py` usava credencial fixa e imprimia sessão/código | Removido; substituído por testes isolados | Ruff completo passou | Git histórico preserva versão antiga; verificar se credencial foi usada fora de teste |
| Média: publicação automática por tag | `.github/workflows/release.yml` publicava em push tag | Somente workflow_dispatch com publish=true e referência tag v; packages:write apenas job publish | Revisão estática | Configurar proteção de branch/ambiente no GitHub; não validada remotamente |

## Evidências executadas

Log integral sanitizado da intervenção: `C:/Users/Caio Tomaz/logs/2026-10-18_07-58-15.log`.

Comandos dentro do runtime Docker `alece-audit-runtime:local` apontado somente ao PostgreSQL efêmero `alece-audit-db-20261018`:

- `pytest -q -p no:cacheprovider --tb=short`: **69 passed** em 19,77s; avisos de staticfiles ausente no bind de desenvolvimento, sem erro.
- `python manage.py check`: sem problemas.
- `python manage.py makemigrations --check --dry-run`: sem drift.
- `python manage.py migrate --noinput`: migrations iniciais e core 0002 aprovadas.
- `python manage.py migrate core 0001 --noinput`, seguido de `migrate --noinput`: downgrade/upgrade core 0002 aprovados em banco efêmero vazio de finanças.
- `ruff check .`: aprovado.
- `docker build -t alece:audit-local .`: exit 0, sem publicação.
- `python -m pip_audit -r /requirements/production.txt`: nenhuma vulnerabilidade conhecida encontrada nas versões resolvidas na data. Não é garantia permanente nem lock de dependências.

Tentativas intermediárias: uma execução de 39 testes auth passou com aviso de conexão persistente na desmontagem; os workers agora fecham conexões. Duas execuções sobrepostas colidiram no mesmo banco `test_alece_audit` (uma com 32 aprovados/1 falha/7 erros; outra com 31 aprovados/3 falhas/38 erros). Causa observada: exclusão/flush concorrente do banco de testes. Esses resultados NÃO foram usados para aprovação. A execução sequencial final de 69 passou; demais testes serão serializados por banco.

## Infraestrutura e limites

- Compose existente não publica PostgreSQL e faz bind web em loopback por padrão. Dockerfile usa usuário não-root. Healthcheck live não substitui readiness; ambos existentes.
- Core 0002 é aditiva: tabela de tentativas e versão de código; não apaga dados financeiros. Reverter código antigo reintroduz vulnerabilidades e pode voltar a aceitar códigos legados: rollback operacional exige manter indisponibilidade e revisar segurança.
- Sem execução de deploy, push, migração de banco persistente, publicação ou alteração de credenciais reais.
- Dependências ainda por faixas; reproduzir resolução antes de implantação. Cookies seguros/TLS dependem do ambiente; não considerar configuração de laboratório pronta para Internet.
- Fontes: https://docs.djangoproject.com/en/5.2/releases/5.2/ ; https://docs.djangoproject.com/en/5.2/ref/models/querysets/ ; https://docs.djangoproject.com/en/5.2/topics/testing/tools/ .

## Backup

`C:/Users/Caio Tomaz/backups/2026-10-18_07-58-15__alece-source.zip`, SHA-256 `882505a179711225c3a2db4526f1ca88dcef09aa190fae4a23ac142d0f2efde5`, checksum e CRC ZIP verificados. Inclui arquivos tracked/untracked não ignorados de entrada, exclui .env/.git/banco. Restore de código deve ocorrer em diretório separado para comparação, preservando alterações posteriores; não usar como backup de DB. Nenhum banco real foi alterado.
