# Desenvolvimento local

A base segue separação entre domínio, serviços e interfaces. O HTML anterior é referência, não parte do backend ativo.

## Rotina de trabalho

1. Realizar diagnóstico do ambiente antes de comandos de alteração.
2. Criar `.env` via bootstrap (sem versionar credenciais).
3. Subir Compose e aplicar migrations somente após backup validado; usar `scripts/deploy.sh`.
4. Para alterar domínio, adicionar teste puro em `tests/test_calculations.py`.
5. Para alterar dados persistentes, adicionar migration e teste de rollback/conversão, revisar impacto no banco e no restore.
6. Criar views/API com autorização no servidor e testes de isolamento entre workspaces e perfis.
7. Migrar HTML de referência gradualmente para componentes reutilizáveis, sem trocar a identidade visual.
8. Abrir PR, aguardar CI e registrar changelog/ADR quando necessário.

## Comandos de trabalho em host **já verificado como compatível**

```bash
bash scripts/verify.sh
# depois de configurar e subir a base:
docker compose exec web python manage.py check
docker compose exec web python manage.py showmigrations
# somente leitura das informações de execução:
docker compose logs --tail=100 web
```

## Contrato de mudanças

Não registrar dinheiro por signals, JavaScript ou ações do Admin sem serviço de transação autorizado. Não associar transação a um perfil financeiro de outro workspace. Não apagar contas com movimentações só porque o saldo é zero. Versionar dados de importação e reverter por lançamentos compensatórios.

## Limitação de validação deste pacote

A construção inicial ocorreu sem Docker e sem download de dependências. Python foi analisado sintaticamente, testes puros executados e YAML/Bash checados. `python manage.py check`, testes com DB, `makemigrations --check` e Docker build devem ser rodados na CI e no host antes de qualquer implantação. Não assumir que já passaram.
