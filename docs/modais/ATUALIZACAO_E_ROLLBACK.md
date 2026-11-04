# Atualização e rollback — Modais ALECE

- **Fonte única:** `ALECE_COMPLETO_DESIGN_SYSTEM_1.0_2026-10-27.zip`, SHA-256 `c690892adc7ff70010651c46da7ad6c1157411a607e08e3ade1ed9d6d29cd046`, verificado antes das alterações.
- **Backup anterior:** `2026-10-27_12-43-50__alece-antes-formularios-modais.zip` em `HOME/backups/`, ao lado de `.sha256`, checksum conferido imediatamente. A cópia da versão anterior permanece disponível nesta sessão; conservar também backup local antes da instalação.
- **Arquivos de aplicação alterados:** `src/view/static/finance/alece.js`, `src/view/templates/finance/base.html`, templates de confirmações de usuários, administração, perfis, histórico de categorização, movimentações, listagem de categorização e visão geral; `src/view/templates/finance/import_preview.html`.
- **Arquivos novos:** `src/view/static/finance/alece_modals.js`, `src/view/static/finance/alece_modals.css`, `tests/modals/test_modals_browser.py`, documentação e relatórios em `docs/modais/`.
- **Migrations:** nenhuma. Modelos financeiros/rotas/identidade/temas não alterados. `.env` e `.env.example` conservados byte a byte. Sem remoção de volumes, logs ou backups.

## Aplicação

1. Em janela de manutenção aprovada, identifique como o ALECE está instalado e confirme acesso administrativo e capacidade de voltar à versão anterior.
2. Faça backup **local**, verifique SHA-256 do ZIP anterior, preserve o `.env` produtivo, o PostgreSQL e os volumes de dados; NÃO restaure `.env` de outro ambiente sem revisão.
3. Verifique SHA-256 do ZIP entregue contra o `.sha256` lateral e seu `MANIFESTO_SHA256.txt` interno.
4. Extraia o ZIP integral **diretamente na pasta `alece`**, sem subpasta; evite copiar ` .env` de amostra sobre credenciais produtivas.
5. Siga o processo do deployment existente para reconstruir/republicar estáticos, se aplicável. Ajuste cache quando necessário. Não reinicie banco nem delete volumes.
6. Execute as regressões em um ambiente de testes e verifique funcionamento de permissões e operações reais antes de expor à produção.

## Reversão

Se houver regressão, pare a promoção, preserve logs e dados coletados, restaure o ZIP de código anterior com hash verificado, publique seus arquivos estáticos correspondentes e execute smoke tests. Como não existem novas migrations, a reversão normal envolve apenas código/estáticos. Evite restaurar PostgreSQL indiscriminadamente se houver lançamentos posteriores ao backup. Nunca remova logs, backups ou volumes automaticamente.
