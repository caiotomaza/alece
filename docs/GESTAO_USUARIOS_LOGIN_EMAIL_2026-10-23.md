# ALECE — Login por usuário ou e-mail e modal de usuário (2026-10-23)

## Funcionalidade
- Usuário obrigatório. E-mail opcional no cadastro, na edição administrativa e nos dados da própria conta.
- Login aceita nome de usuário ou e-mail (comparação sem diferença entre maiúsculas/minúsculas); a senha segue o backend nativo do Django.
- E-mail duplicado entre contas ou colidindo com nome de usuário existente é rejeitado pelos formulários.
- Instalações com e-mails duplicados preexistentes não autenticam por e-mail ambíguo; use o nome de usuário e regularize os e-mails.
- A atribuição de e-mail é protegida pelo formulário da aplicação; o modelo padrão `auth.User` não possui restrição única de e-mail no banco. Se o ambiente admitir gravadores externos ou concorrência intensa, há risco residual de duas gravações simultâneas; considere índice único funcional em migração planejada **após** deduplicar os dados existentes.
- Nome e e-mail não podem ser alterados por administrador de um único núcleo quando a conta é compartilhada por outros núcleos.
- Não houve substituição do modelo de usuário nem migrações novas.

## Visual
- Removido o bloco de contagem de códigos de recuperação do modal de usuários.
- Accordion com superfícies sólidas, seta SVG idêntica à dos selects e botões sem o gradiente artificial.
- Barra de rolagem fina, com contraste apropriado; rolagem pelo teclado e touch mantida.
- Campo E-mail (opcional) adicionado sem retirar campos ou fluxos anteriores.

## Implantação
Faça backup do PostgreSQL, volumes, `.env` existente e código anterior e valide seus SHA-256 antes de implantar. Não exclua volumes (`down -v`). Reconstrua o serviço web conforme seu Compose e verifique a aplicação real.

## Testes de regressão
1. Criar usuário sem e-mail; entrar com usuário e senha.
2. Criar usuário com e-mail; entrar por e-mail e por usuário com a mesma senha.
3. Tentar duplicar e-mail ignorando maiúsculas/minúsculas: erro de formulário.
4. Alterar e remover e-mail na edição e na área Minha conta.
5. Testar conta desativada (não pode entrar), senha errada, login com e-mails históricos duplicados e acesso a outros núcleos.
6. Validar o modal com conteúdos expansíveis, em claro/escuro, desktop e celular, incluindo navegação por teclado.

## Rollback
Restaure os arquivos da versão anterior a partir de `HOME/backups/`, validados via `.sha256`, e reconstrua o serviço. Não houve alteração de esquema; dados de e-mail adicionados às contas não devem ser apagados automaticamente. Preserve os logs e backups.
