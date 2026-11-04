# ALECE — Consistência visual, modais e favicon (23/10/2026)

## Escopo

Atualização de apresentação e comportamento progressivo do frontend, baseada no
site institucional `alece(2).zip` e no favicon SVG enviado. O pacote parte da versão
ALECE com `ALECE_LOG_VALIDACAO` e a correção do HTTP 500 na Visão geral.

- Favicon oficial: `src/view/static/finance/favicon.svg`. É referenciado em páginas
  financeiras, autenticação e setup; o mesmo desenho é usado na marca lateral.
- Títulos das abas principais: apenas seção + `ALECE` (ex.: `Visão geral · ALECE`).
  O nome de perfil e de núcleo não aparece no título do navegador.
- Estilos compartilhados: `src/view/static/finance/alece_ui_consistency.css`,
  importado DEPOIS de `alece.css`; tokens de claro/escuro alinhados ao site institucional.
- Configurações: mosaico adaptativo com Minha conta, Usuários, Perfis, API, Logs e Relatórios.
  Usuários comuns continuam sem o painel administrativo (restrições mantidas no backend).
- Tabelas: cabeçalhos e superfícies seguindo as tabelas financeiras; edição com ícone
  de lápis. Em telas pequenas, as linhas se transformam em registros com rótulos.
- Novo/editar usuário, novo/editar perfil, dados pessoais e integração de IA:
  abrem em diálogo acessível quando suportado. O formulário sempre tem rota própria,
  com CSRF e validação do Django como fallback sem JavaScript.
- Ao submeter o modal de Configurações, validações de erro permanecem no diálogo;
  quando a operação causa redirecionamento de sucesso, a tela de Configurações recarrega.
- Controles booleanos mantêm o `input type=checkbox` nativo, com `accent-color`,
  rótulo associado, foco visível e hit target. A ação de pagamento da Visão geral
  permanece link/botão POST onde já era link/botão; recebeu indicação visual alinhada.

## Implantação segura (Windows PowerShell / Docker Desktop)

1. **Não extraia o ZIP por cima da instalação sem backup.** Preserve seu `.env` atual,
   os segredos gerados e os volumes `alece-db` e de mídia. Confira a instalação atual.
2. Faça backup do escopo a alterar e valide SHA-256 usando `Get-FileHash -Algorithm SHA256`.
   Para rollback completo de uma execução com migração futura, preserve também um
   dump consistente do PostgreSQL antes de iniciar o container novo. A atualização
   desta entrega não adiciona migrations.
3. Extraia em outra pasta. Copie para a instalação APENAS os arquivos do ZIP incremental
   `ALECE_PATCH_UI_2026-10-23.zip`. Esse ZIP **não** inclui `.env`, `compose.yaml`,
   volumes Docker, segredos ou dados financeiros.
4. Rode `docker compose config --quiet` para conferir Compose antes de usar a nova imagem.
   Dentro da pasta `alece`, execute `docker compose up -d --build web`.
5. Confira `docker compose ps`, `docker compose logs --tail 100 web` e
   `http://127.0.0.1:8088/health/live/`. Faça login e navegue em `/configuracoes/`,
   `/visao-geral/` e nas seções financeiras. Teste os modais com usuário administrador
   e tente acessar as funções administrativas como usuário comum para confirmar a
   autorização no servidor.
6. Se houver falha, restaure os arquivos do backup validado com SHA-256, reconstrua
   o serviço `web` e reverta eventuais migrações APENAS com plano específico e backup
   do banco verificado. Não execute `docker compose down -v`.

## Limites da validação feita na entrega

- Passaram verificações de sintaxe Python e JavaScript, consistência dos templates,
  CSS parseável e seis testes estruturais independentes do Django.
- Uma prévia estática das configurações foi conferida no Chromium em larguras
  de 1480px e 390px, nos temas claro e escuro, sem rolagem horizontal.
- A validação visual não substitui teste funcional conectado ao Django.
- **Não** foi executado Docker/PostgreSQL nem testado salvamento real de formulário
  nesta sessão. Não considerar a publicação validada sem os testes do item 5.


### Correção de largura — modal de gerenciamento de usuários (23/10/2026)

O modal administrativo de usuário usa o mesmo limite de largura de 540 px dos formulários padrão, com 24 px de margem total mínima do viewport. A regra conflitante de 790 px foi removida. O formulário mantém padding lateral de 29 px no desktop e 15 px no mobile (até 650 px). Sem mudanças nos endpoints, autenticação, persistência de dados ou migrations.

Se o CSS anterior permanecer visível após a reconstrução da imagem web, atualize a página ignorando o cache do navegador. A validação deve conferir a largura do modal, a legibilidade das colunas e a rolagem vertical nos dois temas.
