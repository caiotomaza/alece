# ALECE — Gestão de usuários e consistência visual (23/10/2026)

## Alterações

Esta entrega é o **projeto integral** e inclui `.env` / `.env.example` com `ALECE_LOG_VALIDACAO=true`, `ALECE_DEBUG=false`, armazenamento persistente de logs em `src/logs/` e todos os módulos anteriores.

### Usuários

- Modal único: identificação e papel no topo; permissões, redefinição de senha e exclusão agrupadas em blocos expansíveis; painel de recuperação com contagem de códigos não utilizados.
- Corrigido JavaScript de vários formulários dentro do mesmo modal: URLs de POST explícitas não são mais substituídas pela rota do modal aberto.
- **Desativação**: editar conta e desmarcar `Conta ativa` (`User.is_active=False`). Autenticação bloqueada pelo backend do Django, com possibilidade de reativação. Mantém associações e auditoria.
- **Exclusão**: endpoint POST `/sistema/usuarios/<workspace_id>/<user_id>/excluir/`, protegido por permissão administrativa, CSRF e confirmação digitada do nome exato. A conta é desativada, o login fica inutilizável e credenciais, recuperação e atributos pessoais diretos são eliminados; o vínculo e grants do núcleo são excluídos. O registro Django permanece como identidade técnica anonimizada, associado aos lançamentos e demais registros `PROTECT`. Esta operação é **irreversível**.
- Não é permitido excluir a própria conta, superusuário global ou o último administrador do núcleo. Usuários presentes em outros núcleos não podem ser excluídos por um administrador de apenas um deles.
- Senhas e códigos **nunca** são exibidos ao administrador. Códigos antigos foram armazenados como hash e não são recuperáveis em texto. O proprietário deve emitir novo conjunto na própria conta para visualizar o valor uma única vez.
- Não foi alterado o schema do banco (sem nova migration). Os seis códigos de recuperação continuam sendo uso único.

### Visual

- Componentes de checkbox com canto arredondado, gradiente sutil, marcação própria e feedback de foco em claro/escuro; fallback nativo em `forced-colors`.
- Inputs, selects e botões com cantos arredondados e cores consistentes. Selects recebem indicador próprio de expansão.
- Formulário em duas colunas no desktop, uma coluna em telas estreitas. Ações alinhadas à direita; no celular, botões de largura integral.
- Modal responsivo com overflow vertical controlado, sem ultrapassar a viewport horizontal.

## Implantação de uma instalação existente

**Antes de copiar os arquivos, faça backup do código e de seu `.env`, exporte PostgreSQL e preserve os volumes de mídia, segredos e tokens**, com hashes SHA-256 verificados. O ZIP contém o programa, **não** os dados financeiros nem os volumes Docker. Não execute `down -v` nem apague os volumes `alece_app_pgdata`, `alece_app_secrets`, `alece_app_media` e `alece_app_ai_tokens`.

1. Extraia o ZIP integral em uma pasta separada; mantenha o nome do projeto Compose (`alece`) para reutilizar volumes, mas não rode duas instalações paralelas usando a mesma stack.
2. Guarde a versão anterior, seus backups e logs em `%USERPROFILE%\backups` e `%USERPROFILE%\logs`. Não substitua um `.env` de produção: preserve suas configurações e adicione `ALECE_LOG_VALIDACAO=true` se necessário. Um `.env` não secreto já acompanha o ZIP para instalações novas.
3. Na raiz do projeto atualizado: `docker compose config --quiet` e `docker compose up -d --build`.
4. Valide `docker compose ps`, `docker compose logs --tail=150 web`, `/configuracoes/` e os fluxos de edição e permissões usando conta de testes. Confira `src/logs/`.
5. A exclusão definitiva deve ser usada apenas após backup validado do banco. Para desfazer uma exclusão, a restauração deve envolver o banco, não apenas o código.

### Rollback

Se não houver alteração de banco, restaure o projeto anterior e seu `.env` preservado e reconstrua `web` sem remover volumes. Caso tenha ocorrido exclusão irreversível de uma conta, recupere a conta a partir de **backup de banco consistente** (e avalie impactos nos registros criados depois). Mantenha os logs e backups.

## Validações desta entrega

- Compilação Python, análise estrutural de template e JS (incluindo URLs explícitas de cada formulário), análise do CSS com parser.
- Prévia estática em Chromium 390 px e 1280 px, ambos os temas: sem overflow horizontal e com os cantos/gradientes esperados.
- Testes de Django foram criados para permissões administrativas, desativação/reativação, preservação de referências e exclusão por confirmação.
- **Não executados**: testes Django/PostgreSQL e E2E de POST no Docker; as dependências não estavam instaladas e a rede de instalação indisponível neste ambiente. Após atualização, executar `docker compose exec web python manage.py test tests.test_user_account_lifecycle_ux` e monitorar falhas.
