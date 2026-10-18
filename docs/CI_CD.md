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

## Dependências

`requirements/*.in` delimitam ranges da linha LTS e atualização planejada. **Ainda não existe lockfile com hashes** no starter. Antes de rotular uma release como reproduzível, gerar lock de dependências completo e validar em CI. Dependabot propõe upgrades em PR para revisão.

## Política de backup e logs

Logs de cada intervenção em `$HOME/logs/YYYY-MM-DD_HH-MM-SS.log`. Backup antes da migração em `$HOME/backups/YYYY-MM-DD_HH-MM-SS__alece-postgresql.dump` + `.sha256` verificado. Nunca remover backups/logs automaticamente. Rollback requer compatibilizar código/schema, não apenas reiniciar contêiner.
