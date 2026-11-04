# CI/CD e governança de mudanças

## Branches

- `main`: sempre validada, protegida por aprovação e CI; sem commit direto em produção.
- Branch de trabalho `feature/...`, `fix/...`, `docs/...`; PR pequeno e reversível.
- Tags `vX.Y.Z` identificam versões; publicar imagem requer execução manual explícita do workflow em uma tag e `publish=true`.
- Mudança de arquitetura/invariante → ADR; mudança funcional → documentação; mudança de schema → migration versionada + testes.

## CI (`.github/workflows/ci.yml`)

- Instalar dependências de desenvolvimento.
- Verificar Python/ruff, `manage.py check`, divergências de migrações e auditar dependências de produção.
- Migrar Postgres de teste e executar `pytest` (unitários e integração).
- Checar Docker build em job independente.
- Não depende do ZimaOS físico nem de acesso às credenciais de produção.

## CD (`.github/workflows/release.yml`)

- Gatilho manual em tag versionada, com `publish=true`, após testes.
- Cria imagem Docker com `docker/build-push-action` e publica no GHCR.
- **Não instala nada automaticamente no servidor pessoal**; ZimaOS precisa receber imagem aprovada, backup verificado e execução assistida do RUNBOOK.
- Para supply chain mais rígida, evolução planejada: pinagem por SHA dos actions, SBOM, assinatura/atestado, scan SCA/containers e atualização automatizada de digests.

## Quality gates

1. Tests/migrations/checks passam.
2. `ruff` sem falhas.
3. PR explica dados modificados, autorização, impactos e rollback.
4. Mudanças de importação CSV/PDF: teste com arquivos malformados, duplicados e sem confiança.
5. Mudanças de permissão: testes de IDOR, isolamento de perfis e perfis combinados.
6. Scripts operacionais: backup com SHA e log; healthcheck funcional após aplicar.

## Gate de validação do ciclo de vida do Compose

O executor local `scripts/Validar-ALECE-Isolado.py` valida o ciclo real
`secrets-init → PostgreSQL → web`, o `env_file` e a interpolação em operações distintas,
o build web/auditoria, verificações Django e a persistência após `down/up` em
`compose.validation.yaml`. O Compose principal tem `container_name` fixos e não deve
ser utilizado com `-p` como único mecanismo de isolamento. O resultado é evidenciado
em `~/test-results/alece_val_isolado_*/resultado.json` e só é homologado se todas as
etapas exigidas tiverem sido executadas e aprovadas. O Docker local é obrigatório.

A geração de `browser.lock` permanece pendente até que a resolução das dependências
transitivas e o teste de instalação com hashes sejam feitos com Python 3.12 e acesso
real ao índice de pacotes. Não substituir `browser.in` na CI por um lock não verificado.

## Dependências

`src/requirements/*.in` delimitam ranges da linha LTS e atualização planejada. Os arquivos `src/requirements/production.lock` e `src/requirements/development.lock` possuem pins e hashes; a CI valida a instalação e monitora novas vulnerabilidades. Dependabot propõe upgrades em PR para revisão.

## Política de backup e logs

Logs de cada intervenção em `$HOME/logs/YYYY-MM-DD_HH-MM-SS.log`. Backup antes da migração em `$HOME/backups/YYYY-MM-DD_HH-MM-SS__alece-postgresql.dump` + `.sha256` verificado. Nunca remover backups/logs automaticamente. Rollback requer compatibilizar código/schema, não apenas reiniciar contêiner.

## Performance manual no CI

O job `performance` roda somente no workflow_dispatch e não utiliza produção; utiliza imagem Chromium `v1.64.1-noble`, PostgreSQL `16-bookworm`, dados sintéticos e arquiva JUnit, HTML e JSON local em `test-results/performance/`. A revisão dos relatórios não gera baseline automaticamente. Não há gate numérico de latência sem calibragem e baseline real.
