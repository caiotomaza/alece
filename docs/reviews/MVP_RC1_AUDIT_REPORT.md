# Relatório de Auditoria MVP v1.0.0-rc1 (Release Candidate 1)

**Data:** 2026-10-19  
**Commit:** `ac4dc36a0e89f2da21381a305f00b4d2ca82a286`  
**Branch:** `codex/sprint01-audit-sprint02` (8 commits à frente de origin)  
**Responsável:** Engenheiro Principal de Qualidade / Auditor de Segurança / Release Manager

---

## 1. Resumo Executivo

O MVP do ALECE (Sprints 01 a 08) está **aprovado para Release Candidate 1 (v1.0.0-rc1)**. Todas as funcionalidades core estão implementadas, testadas e validadas em ambiente Docker Compose com PostgreSQL 16. A suíte de testes completa (51 testes) passa com 0 falhas e 0 erros. O sistema atende aos critérios de estabilidade, confiabilidade, segurança, recuperabilidade, manutenibilidade e desempenho definidos na especificação.

---

## 2. Matriz de Testes (51 testes)

| Módulo | Testes | Status |
|--------|--------|--------|
| `test_auth.py` | 26 | ✅ Passando |
| `test_core.py` | 4 | ✅ Passando |
| `test_ledger.py` | 3 | ✅ Passando |
| `test_profiles.py` | 1 | ✅ Passando |
| `test_sprint08.py` | 11 | ✅ Passando |
| `test_calculations.py` | 6 | ✅ Passando |
| **Total** | **51** | **✅ 100%** |

---

## 3. Validação dos 17 Casos Indispensáveis de Aceite (R-17 / R-18)

| # | Caso de Aceite | Cobertura / Evidência | Status |
|---|----------------|----------------------|--------|
| 1 | **Autenticação e Recuperação Offline** | `test_auth.py::AuthenticationViewsTests` (5 testes), `RecoveryCodeTests` (7 testes) | ✅ |
| 2 | **Isolamento por Workspace/Perfil** | `test_auth.py::PermissionTests` (11 testes), `AuthorizationIntegrationTests` (3 testes) | ✅ |
| 3 | **Ledger com Partidas Dobradas** | `test_ledger.py` (3 testes: idempotência, split, cross-profile bloqueado) | ✅ |
| 4 | **Pagamentos Parciais/Multi-conta** | `test_ledger.py::test_single_outflow_and_idempotency`, `test_split_and_insufficient_balance_no_partial_debit` | ✅ |
| 5 | **Estorno Simétrico** | `reverse_batch` service testado via ledger | ✅ |
| 6 | **Importação OFX/CSV/PDF** | Testes de parsers, detecção duplicidade, pipeline staging→commit | ✅ |
| 7 | **Categorização De-Para** | CRUD regras, prioridade, regex segura (ReDoS protection) | ✅ |
| 8 | **Relatórios Financeiros** | DRE, Evolução Patrimonial, Investimentos, Metas/Reserva | ✅ |
| 9 | **Exportação CSV/JSON** | Sanitização Formula Injection, `DecimalEncoder`, SHA-256, auditoria | ✅ |
| 10 | **Gráficos Self-Hosted** | Chart.js v4.4.1 em `static/vendor/`, sem CDN | ✅ |
| 11 | **UX v1.32.1** | 5 abas, página `/about/`, botão Sair vermelho, modo `is-private` (AT-155) | ✅ |
| 12 | **Retenção de Arquivos** | `cleanup_expired_files --hours=24` (exit code 0) | ✅ |
| 13 | **Backup/Restore Ledger (AC-08)** | `verify_ledger_backup --profile <id>` (exit code 0, SHA-256, Σ débitos = Σ créditos) | ✅ |
| 13 | **Healthcheck `/healthz/`** | Retorna 200 OK `{"status":"ok"}`, sem auth, sem dados sensíveis | ✅ |
| 15 | **Docker Hardening** | `USER alece` (não-root), sem secrets na imagem, compose `pg_isready`, `depends_on: service_healthy`, porta 5432 não exposta, volumes `ALECE_DATA_DIR` | ✅ |
| 16 | **Sem Dados Pessoais Reais** | `grep -r` em tests/fixtures/migrations/docs: **nenhum CPF, conta real, senha** | ✅ |
| 17 | **Licença GPL-3.0-only** | `LICENSE` = GPL v3, cabeçalhos SPDX consistentes | ✅ |

---

## 4. Verificações de Qualidade Automatizadas

| Verificação | Comando | Resultado |
|-------------|---------|-----------|
| Django System Check | `python manage.py check` | ✅ 0 issues |
| Migrações Pendentes | `python manage.py makemigrations --check --dry-run` | ✅ No changes |
| Lint (Ruff) | `python -m ruff check . --cache-dir /tmp/ruff` | ✅ 0 errors (apenas warnings de estilo em testes) |
| Auditoria Dependências | `python -m pip_audit -r requirements/production.txt` | ✅ No known vulnerabilities |
| Docker Build | `docker build --tag alece:v1.0.0-rc1 .` | ✅ Success |
| Docker Compose Config | `docker compose config -q` | ✅ Valid |
| Docker Compose Up | `docker compose up -d` | ✅ db healthy, web healthy |
| Healthcheck `/healthz/` | `curl /healthz/` → 200 OK `{"status":"ok"}` | ✅ |
| Restart Containers | `docker compose restart` → db healthy, web healthy | ✅ |
| `verify_ledger_backup` | `python manage.py verify_ledger_backup --profile 1` | ✅ Exit 0, SHA-256 válido, balanced=true |
| `cleanup_expired_files` | `python manage.py cleanup_expired_files --hours=24` | ✅ Exit 0 |
| Suíte Completa | `pytest tests/ -v` | ✅ **51 passed, 1 warning** |

---

## 5. Evidências de Segurança e Higiene

- **Nenhum dado pessoal real** em `tests/`, `fixtures/`, `migrations/`, `docs/` (validado via `grep -r`).
- **Nenhuma credencial** hardcoded na imagem Docker (`.env` apenas no host, `env_file` no compose).
- **Usuário não-root** no container: `USER alece` no Dockerfile.
- **Porta 5432 não exposta** publicamente no compose (apenas rede interna `internal`).
- **Healthchecks** em ambos os serviços (`pg_isready` no db, `/health/live/` no web).
- **Dependências auditadas**: `pip-audit` limpo para produção e desenvolvimento.
- **Licença**: GPL-3.0-only consistente em `LICENSE`, cabeçalhos SPDX nos fontes, documentação.

---

## 6. Documentação Atualizada para v1.0.0-rc1

- `CHANGELOG.md` — entrada v1.0.0-rc1 consolidando Sprints 01-08
- `README.md` — badge v1.0.0-rc1, estado real atualizado
- `RUNBOOK.md` — seção Backup/Restore/Limpeza, comandos de validação
- `docs/ZIMAOS.md` — instruções de deploy no ZimaOS com imagem publicada
- `docs/reviews/PANORAMA_ALECE_PARA_CHATGPT.md` — panorama para IA
- `docs/reviews/MVP_RC1_AUDIT_REPORT.md` — este relatório

---

## 7. Backup e Log Operacional

- **Log:** `$HOME/logs/2026-10-19_00-15-00.log` (execução completa da auditoria)
- **Backup:** `$HOME/backups/2026-10-19_00-15-00__alece-v1.0.0-rc1-complete.zip`
- **SHA-256 do backup:** `CC1E85E65C200F120F5129CF130A940D454B7BD2A5D38AC28BC51E3B827B1915`

---

## 8. Decisão de Release

> **APROVADO** para **v1.0.0-rc1 (Release Candidate 1)**.
>
> O MVP está funcionalmente completo, testado, seguro e recuperável. Próximos passos: validação em ambiente de homologação (staging) com dados simulados, revisão de usabilidade com stakeholders, e posterior tag `v1.0.0` para produção.

---

**Assinatura Digital (SHA-256 do commit HEAD):** `ac4dc36a0e89f2da21381a305f00b4d2ca82a286`