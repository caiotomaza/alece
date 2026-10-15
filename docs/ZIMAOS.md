# ZimaOS — estratégia de self-host

A documentação do fabricante confirma **suporte a apps Docker Compose personalizados**. O repositório possui Compose de desenvolvimento construindo imagem localmente. Para importação pela UI do ZimaOS, normalmente é melhor usar uma imagem pronta publicada no GHCR, porque o editor de Compose pode não ter contexto de build local.

## Fluxo recomendado

1. Confirmar versão do ZimaOS, arquitetura, disponibilidade de Compose e permissão de implantação.
2. Fazer build/testes na CI, gerar imagem GHCR por tag e validar digest/compatibilidade de CPU.
3. Confirmar pasta persistente, política de backup e port mapping antes de migrar dados reais.
4. **Copiar** o Compose para uma variante apropriada ao ZimaOS: substituir `build: ...` por `image: ghcr.io/<usuario>/<repo>:<tag>` aprovado; não assumir placeholders como valores reais.
5. Adotar segredos via variáveis/arquivo restrito no host. Não colocar `ALECE_DB_PASSWORD` em repositório público nem YAML compartilhado.
6. Ajustar `ALECE_BIND_IP` e `ALECE_ALLOWED_HOSTS` conforme a LAN real. A base não obriga HTTPS para prototipação local, mas não exponha login por HTTP a redes não confiáveis.
7. Após testar `GET /health/ready/`, confirmar backup e criar acesso inicial, executar smoke tests das rotas reais quando implementadas.

## App Store (posterior)

Publicação como pacote de loja ZimaOS `Apps/ALECE/docker-compose.yml`, ícone e bloco `x-casaos` é **uma etapa separada**, não necessária para o primeiro desenvolvimento. Verificar o schema atual da loja no momento da publicação; não misturar metadados de loja com o compose de desenvolvimento.

## Referências oficiais

- https://www.zimaspace.com/docs/
- https://www.zimaspace.com/docs/developer/app-store-compose-x-casaos
- https://www.zimaspace.com/docs/zimaos/app-store/paperless-ai-install
- https://docs.docker.com/compose/how-tos/startup-order/
