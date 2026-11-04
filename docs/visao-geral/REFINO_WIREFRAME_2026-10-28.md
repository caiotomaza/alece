# ALECE — Refinamento da Visão geral conforme wireframe

Data: 28/10/2026. Base exclusiva: `ALECE_COMPLETO_SEM_BLOCO_DETALHES_2026-10-28.zip`, com SHA-256 verificado antes da extração. Backup integral anterior e checksum validados em `~/backups/`; log mantido em `~/logs/` no ambiente de edição.

## Modificações solicitadas

- Retirados o fundo colorido, contorno e espaçamento da *moldura externa* dos quatro cards. A superfície, as bordas e os tokens originais de cada card continuam presentes; não houve troca de identidade ou tema.
- Removido o botão de edição do cabeçalho **Planejamento mensal**. O atalho do card superior **Renda** permanece disponível quando autorizado, para não retirar o acesso existente à edição.
- Sem dados para planejamento, o texto exibido passa a ser exatamente: **O sistema não tem informações suficientes para gerar os dados.** O aviso anterior, o texto sobre valores desconhecidos e o botão "Informar renda" saíram desse estado vazio.
- Removido somente o aviso abaixo da tabela "Este mês" sobre movimentação auditável, preservando **todas** as confirmações, URLs e formulários reais.
- No desktop, os painéis Planejamento e Este mês têm a mesma altura geométrica (490px). A tabela de compromissos utiliza a largura disponível, com cabeçalho fixo e rolagem interna quando as linhas ultrapassam a altura útil. O planejamento também possui rolagem interna e foco de teclado para que o rodapé permaneça visível. Na experiência móvel os painéis empilham e o planejamento apresenta seu conteúdo completo; a lista mensal limita a altura e conserva rolagem horizontal apenas se necessária.
- Tabela mensal em telas largas: colunas proporcionais para reduzir rolagem horizontal; o texto longo quebra linha dentro das células, sem alterar dados ou esconder colunas. Em dispositivos estreitos há largura mínima interna e rolagem própria.

Arquivos de execução afetados:

- `src/view/templates/finance/workspace_page.html`
- `src/view/static/finance/alece_overview.css`

Arquivos de QA ajustados/adicionados:

- `scripts/quality/verify_overview_layout.py` (catálogo com grande quantidade de linhas fictícias)
- `tests/design_system/test_overview_wireframe_contract.py`
- `tests/design_system/test_overview_refinement.py`
- `docs/visao-geral/evidencias/refino_*.png` e `resultado_viewports_refino.json`

Nenhum modelo, migration, JS de produção, rota, permissão, regra financeira, integração, banco ou `compose` foi modificado. `.env` e `.env.example` foram preservados byte a byte em relação ao ZIP recebido.

## Validação e limitações

- `ALECE_TEST_ISOLATED=1 ALECE_DB_NAME=test_alece ALECE_DB_HOST=localhost pytest -q tests/design_system`: **20 testes aprovados**, com aviso de `pytest-django` ausente.
- `python scripts/quality/verify_overview_layout.py`: **10 combinações** (320, 390, 768, 1280 e 1920 px CSS; temas claro e escuro), todas sem overflow horizontal da página, com o rolamento da tabela restrito ao card. Nos tamanhos desktop, as alturas dos dois painéis coincidiram na prévia.
- Evidências: `docs/visao-geral/evidencias/refino_{light,dark}_{320,1280}.png`, `resultado_viewports_refino.json`.
- **Importante:** as imagens são de **catálogo sintético** com os CSS de produção, não páginas Django autenticadas. As ações de pagamento e estorno **não foram executadas**. Os testes integrados com Django/PostgreSQL de homologação e com usuários reais são **pendentes**, não aprovados.

## Implantação e rollback

1. Antes de implantar, faça backup verificável da instalação atual, do `.env` produtivo e dump nativo PostgreSQL, com SHA-256, mantendo os arquivos em `$HOME/backups/` e logs em `$HOME/logs/`. Confirme a integridade do ZIP novo.
2. Extraia os arquivos do ZIP diretamente em `alece` (sem pasta superior), sem substituir o `.env` produtivo sem revisão. Reconstrua apenas o serviço web pela rotina Docker Compose validada do ambiente, mantendo os volumes do banco.
3. Verifique tema claro/escuro, viewport desktop/celular, tabela com dezenas de itens e estados vazios. Teste as ações de pagamento e estorno com usuários e perfis autorizados em homologação.
4. Se ocorrer regressão, restaure o ZIP anterior do backup com checksum validado e recrie apenas o serviço web. **Não reverta o PostgreSQL automaticamente:** nenhuma migration foi produzida, e um rollback de banco poderia apagar lançamentos recentes.

Não execute `docker compose down -v`, `docker volume prune`, remoção de logs ou limpeza de banco de dados.

## Referências técnicas

- MDN — [CSS overflow](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/overflow): contenção de overflow por painel.
- MDN — [CSS overscroll-behavior](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/overscroll-behavior): prevenção de propagação da rolagem.
- Django — [proteção CSRF](https://docs.djangoproject.com/en/5.2/howto/csrf/): preservação de POST com token.
