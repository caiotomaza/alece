# BUILD_REPORT — ALECE DevKit v0.1.0

Data de preparação: 2026-10-15.

## Resultado das verificações executadas no ambiente de criação

- LICENSE copiada sem modificação: **SHA-256 `3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986`**.
- Protótipo visual v1.32.1: cópia binária **idêntica** ao arquivo de entrada.
- Especificação v1.32.1: cópia binária **idêntica** ao arquivo de entrada.
- AST Python: **26 arquivos** verificados sem erro de sintaxe.
- Sintaxe Bash: `bash -n` executado com sucesso para todos os scripts `scripts/*.sh`.
- YAML: analisado com PyYAML para Compose, GitHub workflows e Dependabot.
- Testes de domínio puro: **6 de 6 aprovados** em `tests/test_calculations.py`.

## Não foi possível executar nesta sessão

- Docker build e Docker Compose, porque Docker Engine não está presente.
- Instalação Django/Psycopg e execução do projeto; o acesso a pacotes está indisponível no container.
- Migrações no PostgreSQL, Django `check`, `makemigrations --check` e testes de integração: configurados na CI, **não executados aqui**.
- Deploy, restauro real, autenticação final, segurança de host ZimaOS e conciliação bancária.

## Observação

Esta é uma base de desenvolvimento **não certificada para produção**. Antes de usar com dados pessoais reais, completar os gates de `docs/ROADMAP.md` e validar os workflows de CI em GitHub.
