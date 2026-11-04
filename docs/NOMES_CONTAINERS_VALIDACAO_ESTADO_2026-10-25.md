# ALECE — Nomes dos containers, diagnóstico, evidências e risco operacional

## Ambiente observado em 25/10/2026

Fonte: logs `2026-10-25_16-15-05.log` e `Texto colado(20261025-165740).txt` fornecidos pelo operador, não uma execução Docker neste ambiente.

- `secrets-init-1` terminou com exit 0 e informou segredos prontos. **Sucesso esperado de job one-shot**, não falha.
- `db-1`: PostgreSQL 16.15 iniciou, migrações foram aplicadas.
- `web-1`: checks de rotas, templates, estáticos, banco, esquema e volumes em estado OK; Gunicorn iniciou.
- Navegação autenticada: `/configuracoes/`, `/logs/`, `/relatorios/`, `/despesas/`, `/investimentos/`, `/movimentacoes/`, `/visao-geral/` responderam HTTP 200.
- Health endpoint `/saude/pronto/` respondeu HTTP 200 repetidamente.
- **Pendência:** Django `urls.W005`: namespace `admin` registrado duas vezes em `src/web.py` (rotas `/admin/` e `/administracao/`). Não corrigido nesta mudança limitada a nomes e evidências; requer teste de compatibilidade dos links administrativos.
- Registro final `SIGTERM` ocorreu após `docker compose up` em modo anexado, encerrado com Ctrl+C, não evidência de crash da aplicação.
- O log **não contém a saída do pytest**, testes CRUD completos, restauração de banco, migrações reversíveis nem teste de carga. Não concluir cobertura total.

## Serviços e nomes

| Serviço Compose (DNS interno) | Nome Docker/Portainer | Responsabilidade | Execução esperada |
|---|---|---|---|
| web | alece_web | Gunicorn/Django, HTTP 8000 interno | running e healthy |
| db | alece_db | PostgreSQL persistente | running e healthy |
| secrets-init | alece_secrets_init | inicializar segredos no volume compartilhado | exited (0) |

**Não existe um serviço `app` separado no Compose atual.** O processo Django é o serviço `web`; criar `alece_app` extra seria redundante ou incorreto. A nomenclatura reservada para serviço `app` só será adotada quando houver um processo distinto, como worker de tarefas.

Os nomes personalizados impedem escalabilidade por replicas com Compose e podem conflitar se mais de um ALECE for executado no mesmo daemon Docker. A rede `alece_internal` e os volumes `alece_app_pgdata`, `alece_app_secrets`, `alece_app_media`, `alece_app_financial_backups` e `alece_app_ai_tokens` não foram alterados. O `ALECE_DB_HOST=db` também permanece.

## Onde consultar os resultados

| Resultado | Origem | Local |
|---|---|---|
| Checks de inicialização, migrations e Gunicorn | docker/logged_start.py + docker/start.sh | `alece/src/logs/YYYY-MM-DD_HH-MM-SS.log` |
| Teste completo de regressão (pytest) | `.github/workflows/ci.yml` | GitHub Actions, job `python`, artefato `alece-pytest-results/pytest.xml` |
| Smoke/read-only de runtime Windows | `scripts/Relatorio-Validacao-ALECE.ps1` | `%USERPROFILE%\logs\YYYY-MM-DD_HH-MM-SS.log` |
| Health periódico | Docker healthcheck | `docker compose ps` / status da engine |

A CI só fornece resultado após rodar. Não afirmar que a suite passou sem acessar a respectiva execução do workflow.

## Critérios de qualidade antes de declarar produção

1. `manage.py check --deploy` ajustado para ambiente com proxy/TLS real; eliminação de `urls.W005`.
2. Testes de CRUD e autorização para cada módulo com PostgreSQL isolado.
3. Provas de integridade do ledger, estornos, importações e idempotência.
4. Teste de restauração de backup em ambiente independente e verificação SHA-256.
5. Testes de autenticação, códigos de recuperação, cookies, CSRF e controle de acesso.
6. CI verde com JUnit, lint e auditoria de dependências.
7. UX móvel/acessibilidade (navegação teclado, modal, tema), recuperação de erro e regressão visual.
8. Monitoramento operacional, atualização segura e plano de rollback exercitado.

## Implantação segura em máquina já instalada

1. Obtenha um dump consistente do PostgreSQL, gere e valide SHA-256; guarde cópia externa. Preserve também `.env` e volumes críticos.
2. Copie a nova versão completa do ALECE mantendo o projeto Compose `alece` e os volumes existentes.
3. Inspecione `docker compose config --services` e `docker compose ps -a`; não imprima configuração completa com segredos em logs.
4. Com backup validado, execute `docker compose up -d --build`. A mudança de `container_name` recria containers, mas mantém volumes nomeados. Não use `down -v` nem `--renew-anon-volumes`.
5. Valide `alece_web`, `alece_db`, e `alece_secrets_init` (`Exited (0)`), mais o endpoint de saúde e as rotas.
6. Execute o diagnóstico PowerShell e examine o log na HOME do usuário.
7. Em falha, restaure o `compose.yaml` e demais arquivos do backup e rode `docker compose up -d` para retornar aos nomes anteriores; se mudanças de versão tiverem alterado o banco, restaure o dump testado.

**Riscos:** reconstrução pode causar indisponibilidade temporária; startup do ALECE executa migrações automáticas, portanto o backup de banco é obrigatório mesmo que a alteração proposta seja apenas nos nomes. A implantação não foi executada neste ambiente.

## Evidência de testes desta ENTREGA

Validações estáticas locais, em cópia extraída e isolada do projeto: integridade ZIP/SHA-256, Parse YAML Compose, AST Python, regressão estrutural de nomes, testes de domínio sem Django e preservação do volume/DNS. Esta entrega **não** executou Docker, Django com PostgreSQL nem suíte pytest. O relatório final e os checksums constam do registro de geração do pacote.
