# Atualização e rollback — ALECE Design System 1.0

**Escopo:** arquivos estáticos e templates. **Sem migrations, alteração de banco, rotas, políticas, telemetria ou serviços.**

## Antes de aplicar em produção

1. Preservar ZIP anterior e seu `.sha256`; gerar backup validado e SHA-256 do diretório operacional e registrar sua localização. Criar **separadamente** backup nativo do PostgreSQL e dos volumes por política de recuperação, embora esta alteração não os modifique.
2. Comparar `.env` do ZIP com o `.env` em produção; não sobrescrever segredos em uso. Não expor credenciais nos logs de atualização.
3. Em ambiente de homologação executar `python manage.py check`, `pytest`, `collectstatic --noinput` (conforme o Dockerfile/serviços instalados) e verificar build/servidor. Não executar migrations sem inspeção prévia; nenhuma foi incluída nesta entrega.
4. Extrair o ZIP **na raiz da pasta `alece`**, sobrepondo apenas os arquivos do projeto; não apagar volumes, logs ou backups. Recriar apenas o processo de aplicação que serve os arquivos estáticos, se exigido pela estratégia de deploy.
5. Invalidar cache de CSS se necessário; verificar em desktop/mobile e claro/escuro as telas com dados financeiros fictícios, filtros, dropdowns, botões, tabelas, gráficos, modais e mensagens. Conferir acesso por perfil e navegação por teclado.

## Rollback

Se houver regressão visual/funcional, restaurar a versão anterior do **código/estáticos/templates**, validada pelo SHA-256 de seu ZIP, na mesma pasta raiz. Recoletar estáticos e recarregar somente o serviço web se necessário. **Não restaurar automaticamente o banco de dados** ou volumes: código não executou migrations nem alterou esquema. Preservar os arquivos de log antes e depois do rollback para diagnóstico.

## Arquivos de backup e SHA-256

O ZIP anterior foi preservado no diretório HOME da intervenção em `backups/YYYY-MM-DD_HH-MM-SS__alece-design-system-prealteracao.zip`, com `.sha256` verificado. O ZIP atualizado inclui manifesto SHA-256 de seus próprios arquivos e arquivo `.zip.sha256` externo. O caminho de HOME do contêiner de análise **não é o caminho do servidor produtivo**; crie backup e log locais antes de aplicar.
