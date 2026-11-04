# ALECE — Evidências de testes e avaliação em 25/10/2026

## 1. Evidência real da instalação do usuário

Fonte: `2026-10-25_16-15-05.log` e transcrição do `docker compose up` enviados na conversa; não é acesso remoto ao ambiente.

**Aprovado pelo log de inicialização:**

- `secrets-init` encerrou normalmente com código 0;
- PostgreSQL 16.15 pronto para conexões, banco e migrações aplicados;
- verificações de startup `rotas`, `templates`, `estaticos`, `banco`, `schema` e `volumes`: **OK**;
- Gunicorn 23.0.0 aceitando requisições;
- endpoint `/saude/pronto/` respondendo HTTP 200 repetidamente;
- páginas principais testadas manualmente no navegador respondendo HTTP 200 (os códigos HTTP não comprovam operações internas de CRUD).

**Aviso ainda presente:** `urls.W005` (namespace `admin` duplicado). É dívida técnica de roteamento e não foi alterado no escopo desta entrega.

**Não houve saída da suíte `pytest` nessa inicialização.** A suíte não roda no startup por design.

## 2. Validações EXECUTADAS nesta entrega de nomes e relatórios

Data da execução local: 25/10/2026. Ambiente desta análise, fora do Docker do usuário.

- Integridade SHA-256 do ZIP de origem: aprovada.
- Backup de arquivos alterados com SHA-256 validado: aprovado.
- Compose YAML e preservação de dependências/volumes: aprovados.
- Regressão `unittest` (estrutura + cálculo financeiro): **29 testes, 29 aprovados, 0 falhas, 0 erros**.
- Análise AST dos arquivos Python: **164 arquivos, sem erros de sintaxe**.
- ZIP resultante: integridade interna e SHA-256 validados.

**Não executado neste ambiente:** Docker Compose real, Django com PostgreSQL, `pytest` completo, CI GitHub Actions, testes E2E autenticados, restore de backup e análise de carga. Não declarar essas verificações como aprovadas.

## 3. Local dos resultados

- Logs startup do Docker: `alece/src/logs/YYYY-MM-DD_HH-MM-SS.log`, `ALECE_LOG_VALIDACAO=true`.
- Diagnóstico do runtime no Windows: execute `scripts/Relatorio-Validacao-ALECE.ps1`; gera `%USERPROFILE%/logs/YYYY-MM-DD_HH-MM-SS.log`.
- Testes completos no GitHub Actions, job `python`: comando `pytest -q --junitxml=test-results/pytest.xml` e artefato `alece-pytest-results`, disponível quando houver execução do workflow.
- A validação executada para montar este ZIP também está registrada em log no ambiente de geração; esse log não é um resultado do ambiente do usuário.

## 4. Avaliação

**Estado:** projeto em desenvolvimento funcional, infraestrutura básica operante nos logs apresentados, mas sem evidência suficiente para produção crítica.

**Prioridades:** (P1) corrigir `urls.W005` preservando compatibilidade de rotas; (P1) CI completa verde com PostgreSQL real; (P1) restaurar backup testado e conferir ledger/estornos/importação; (P2) exercitar autenticação e isolamento de perfis/usuários; (P2) ensaiar deployment/rollback e monitoramento; (P3) refinar UX, documentação e medição de desempenho.

A alteração de nome de containers, embora cosmética na lógica do software, **recria containers** quando aplicada. Os volumes persistentes e a rede foram deixados sem alterações. O script de startup existente aplica migrações automaticamente; backup de PostgreSQL é obrigatório antes do deploy.
