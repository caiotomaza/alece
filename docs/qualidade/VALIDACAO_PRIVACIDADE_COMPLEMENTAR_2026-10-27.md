# Evidências de validação — auditoria complementar em 27/10/2026

## Ambiente da execução

- Máquina de auditoria: Linux x86_64 em container efêmero; Python 3.13.5; Node.js 22.16.0.
- Dependências *indisponíveis*: Django, pytest-django, psycopg e servidor PostgreSQL. `docker` e `psql` não disponíveis. Sem acesso ao banco de produção.
- Base: ZIP fornecido no pedido atual, SHA-256 `6b98bd3e03d8cf945878ca2c2c8bfd147c932212b58a528fda0a08a7ada6af1d`.
- Backup de origem: `HOME/backups/YYYY-MM-DD_HH-MM-SS__alece-pre-auditoria.zip`; SHA-256 validado (`OK`). Backup mantido fora do novo ZIP para não duplicar código antigo.
- Log: `HOME/logs/YYYY-MM-DD_HH-MM-SS.log` e cópia resumida de evidências nesta entrega. Caminho HOME refere-se ao executor da auditoria, não ao host produtivo do usuário.

## Resultados realmente obtidos

| Etapa | Estado | Observação |
| --- | --- | --- |
| Verificação estrutural do ZIP anterior | APROVADO | 391 entradas; 391 preservadas, inclusive `.env` e `.env.example` |
| Backup integral de entrada | APROVADO | SHA-256 calculado e verificado após cópia |
| Inspeção estática direcionada | CONCLUÍDA | Auth, recuperação, sessão, controle de acesso, IA, logs, XLSX/CSV, importação, cookies/cabeçalhos, templates e tráfego externo estático |
| `python -m compileall -q src/controller tests` | APROVADO | Compilação Python, **não** prova de comportamento |
| `node --check` JS de dashboard com marcadores Django | APROVADO após correção | A primeira execução encontrou duas chaves de fechamento ausentes; corrigido e revalidado |
| `pytest` apenas testes executáveis sem Django | **45 aprovados**, 11 subtestes | Ver JUnit `docs/qualidade/evidencias/auditoria_privacidade_2026-10-27_puros.xml`; aviso normal: opção pytest-django desconhecida |
| Tentativa inicial de coletar arquivo de teste que importa Django | BLOQUEADA | `ModuleNotFoundError: No module named 'django'`; suíte reduzida foi reexecutada com aprovação |
| Instalação de dependências em venv isolada | NÃO CONCLUÍDA | Falha na resolução DNS do índice pip; nenhum pacote adicionado ao projeto |
| `tests/reports/test_safe_dashboard_chart_data_20261027.py` (HTTP/PostgreSQL) | NÃO EXECUTADO | Teste preparado, sem Django e DB disponíveis |
| Suíte integrada completa, testes de navegador e `check --deploy` | NÃO EXECUTADO | Sem ambiente de teste isolado funcional |
| `makemigrations --check --dry-run` | NÃO EXECUTADO | Sem Django/PostgreSQL; arquivos de migration existentes não foram alterados |
| Tráfego real de IA, dados do operador, testes de produção | NÃO EXECUTADO | Intencionalmente não acessados |

## Pré-condições para aprovar a instalação

1. Executar CI e testes Django completos em PostgreSQL isolado **sem** montar `app_pgdata`, `app_ai_tokens`, `app_secrets`, `app_media` nem `.env` produtivos; usar o fluxo de testes isolados já presente no repositório.
2. Executar o novo teste `tests/reports/test_safe_dashboard_chart_data_20261027.py` e toda suíte existente com o banco sintético. Validar isolamento de perfis, revogação de sessões, CSRF e exclusividade de API.
3. Validar o HTML/JavaScript do dashboard no navegador real, em zoom 200%, mobile e ambos os temas. Esta etapa NÃO prova conformidade WCAG.
4. Verificar migrações e `manage.py check --deploy` no ambiente TLS/reverse proxy pretendido.
5. Conferir logs reais e exportações por operador autorizado, sem compartilhar dados financeiros nem credenciais com terceiros.

**Liberação de produção: PENDENTE.** Não considerar os 45 testes estáticos como aprovação de regressão funcional ou prova de ausência de vazamento.

## Atualização segura e rollback (orientação, não executados no host do usuário)

1. Identificar SO, Docker/Compose, privilégios, volumes e proxy da instalação. Confirmar acesso administrativo e plano de recuperação.
2. Antes de substituir arquivos, criar e validar backups **separados** do projeto (incluindo `.env` atual), PostgreSQL e volumes persistentes, cada um com SHA-256 e lugar de recuperação fora de contêiner efêmero.
3. Verificar SHA-256 do ZIP desta entrega e revisar alterações. **Não sobrescrever `.env` produtivo sem primeiro compará-lo** com o exemplar incluso, mesmo que o ZIP contenha `.env` conforme solicitado.
4. Após testes isolados aprovados, extrair **o conteúdo na raiz da pasta `alece`** (o ZIP não contém uma pasta de encapsulamento), preservando volumes, dados, logs e backups.
5. Reconstruir/reiniciar somente o serviço web afetado quando necessário, sem remover volumes; rodar checks, migrations dry-run, healthcheck real, login, permissões, relatórios, gráficos, importação/exportação, duas interfaces de tema e IA somente com dados sintéticos e autorização.
6. Em falha, interromper novas escritas e restaurar os arquivos do ZIP/base anterior cujo SHA-256 consta acima. Restaurar o banco/volumes **somente após avaliar** alterações de dados desde o backup, evitando perda de lançamentos novos. Nenhuma migration foi criada por esta entrega.

Preservar todos os logs, backups e artefatos de teste para rastreabilidade. Serviços e dados reais **não** foram alterados por esta auditoria.
