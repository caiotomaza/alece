# ALECE — Remoção do bloco expansível na Visão geral

**Data:** 28/10/2026. **Base:** ZIP integral `ALECE_COMPLETO_VISAO_GERAL_WIREFRAME_2026-10-28.zip`, com SHA-256 validado.

## Alteração solicitada

- Removidos da Visão geral o botão **“Ver contas, investimentos e distribuição detalhada”** e o conteúdo inteiro do antigo `<details id="overview-details">`.
- Mantidos os quatro cards do wireframe: Renda, Saldo, Planejamento mensal e Este mês.
- O ícone do indicador de Saldo passa a abrir a página preexistente de contas do perfil (`finance:profile-detail`) quando **um único perfil** com permissão de visualizar contas está selecionado. Com múltiplos perfis ou sem autorização, o atalho não é exibido; a informação agregada do saldo continua visível conforme autorização.
- Removido o carregamento do JavaScript que só existia para abrir esse bloco. Seu arquivo permanece no projeto, sem execução. Não foram alterados cálculos financeiros, APIs, models, migrations, sessão, perfil selecionado, rotas, CSS global, permissões ou banco de dados.
- Tabelas de contas e investimentos continuam disponíveis nas páginas já existentes com as respectivas permissões. O gráfico circular antigo foi removido somente da página inicial; nenhum registro financeiro foi eliminado.

## Testes e limites

- `pytest -q tests/design_system/test_overview_wireframe_contract.py`: executar no ambiente de build.
- `python scripts/quality/verify_overview_layout.py`: prévia em Chromium com dados fictícios (não é uma renderização do Django).
- Testes integrados Django/PostgreSQL e homologação no ambiente produtivo: **pendentes se não explicitamente registrados como concluídos no log**.

## Atualização segura

1. Gere backup e SHA-256 do ZIP atual e um dump independente do PostgreSQL antes de implantar. Preserve o `.env` produtivo e os volumes.
2. Confira o SHA-256 do novo pacote; extraia os arquivos diretamente na raiz de `alece`, sem criar subpasta adicional.
3. Recrie apenas o serviço web conforme sua orquestração atual, mantendo o banco e os volumes. Não utilize `docker compose down -v`.
4. Atualize a página e valide os quatro cards, o atalho de Saldo, o perfil selecionado e a confirmação de pagamento/estorno.

## Rollback

Restaure o código e os assets do ZIP anterior a partir do backup com hash validado e reinicie somente o serviço web conforme necessário. **Não reverta o banco**, pois esta alteração não o modifica. Mantenha os backups e logs.

## Resultados observados nesta execução

- **5 testes estáticos Playwright/contrato:** aprovados (uma execução inicial precisou atualizar a asserção obsoleta que ainda exigia o script removido).
- **Prévia Chromium:** 10 combinações de largura (320, 390, 768, 1280 e 1920 CSS px) e tema (claro/escuro) executadas, sem overflow horizontal global nas páginas sintéticas.
- **Compilação de arquivos Python modificados:** aprovada.
- **Inspeção do template:** trecho expansível, título antigo, link-âncora órfão e carregamento do script removidos.
- **Aviso de pytest:** `pytest-django` não está instalado neste ambiente; os testes de Django/PostgreSQL não foram executados.
- **Capturas em `docs/visao-geral/evidencias/sem_detalhes_*.png`:** catálogo estático com valores fictícios; não representam homologação da aplicação autenticada.
- **Migrations:** nenhuma. **Dados e configurações do projeto:** `.env` e `.env.example` preservados, sem acesso ao banco de produção.
