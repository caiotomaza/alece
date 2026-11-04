# ALECE — Exibição e segurança dos códigos de recuperação

## Interface

- Modal padronizado a **540 px** no desktop e com adaptação para celulares.
- Quando um novo conjunto de seis códigos é emitido, todos são apresentados imediatamente.
- Durante a emissão, há botões **Copiar códigos** e **Baixar .txt**, com a confirmação de salvamento já existente.
- Removidos os links **Voltar** e **Redefinir os seis códigos** da consulta de estado.
- Para o usuário que já confirmou um conjunto, a janela mostra a quantidade disponível sem revelar os segredos.
- A opção **Resetar códigos de recuperação** permanece na página Configurações e exige a senha atual. Em caso de emissão interrompida, a janela de pendência apresenta um link textual para a recuperação do fluxo, evitando bloqueio da conta.

## Restrição criptográfica

Os códigos antigos **não são recuperáveis**. O banco contém apenas hashes, e não texto original. É impossível exibi-los a partir desses hashes. Esta entrega não enfraquece o armazenamento nem revoga silenciosamente os seis códigos ao abrir a tela.

Para exibir um conjunto novo, o usuário deve solicitar explicitamente a substituição pela ação de Configurações. Após informar a senha atual, os novos seis códigos serão exibidos no mesmo modal, prontos para cópia e download. Os antigos deixam de valer nesse momento.

## Validação e rollback

1. Antes de atualizar sua instalação, faça backup validado por SHA-256 do banco PostgreSQL, volumes Docker, `.env` e código atualmente instalado.
2. Preserve os volumes existentes; nunca execute `docker compose down -v`.
3. Na raiz do novo projeto, execute `docker compose up -d --build web` somente após ter um rollback testado.
4. Verifique a emissão no primeiro acesso e o reset autorizado; depois confirme que a consulta posterior não revela os códigos antigos.
5. Os logs de cada execução estão em `src/logs` quando `ALECE_LOG_VALIDACAO=true`.
6. Para desfazer, restaure a versão anterior do código e a configuração anterior; os dados financeiros não sofreram migrações nesta correção.

**Nenhum teste funcional Docker/PostgreSQL foi executado neste pacote.**
