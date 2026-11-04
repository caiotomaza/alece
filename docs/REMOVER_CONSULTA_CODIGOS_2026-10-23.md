# Remoção da opção "Ver códigos de recuperação"

## Comportamento

- `Configurações > Minha conta` contém **Editar suas informações**, **Resetar senha** e **Resetar códigos de recuperação**.
- Removidos a opção **Ver códigos de recuperação**, seu modal de estado e o rodapé com contagem de códigos.
- A URL histórica `/configuracoes/codigos/` é mantida porque faz parte da **configuração inicial obrigatória e da confirmação da emissão** dos códigos.
- GET dessa URL por usuário que já confirmou seus códigos redireciona para `/configuracoes/` (sem mostrar modal).
- Primeiro acesso sem códigos: emite seis códigos para exibição única, com **Copiar**, **Baixar .txt** e confirmação.
- Primeiro acesso interrompido ou códigos esgotados: redireciona ao formulário de geração com senha atual; não revela hashes nem apaga dados automaticamente.
- O botão **Resetar códigos de recuperação** continua disponível. A substituição exige senha atual; os códigos antigos são invalidados somente quando os novos são emitidos.

## Segurança

Os seis códigos anteriores estão armazenados somente como hashes e não podem ser reexibidos. Nenhum código foi regenerado ou revogado durante a criação do pacote. O fluxo de emissão continua usando a verificação e o formulário existentes.

## Implantação

Antes de atualizar, preserve o `.env` existente, os segredos Docker e os dados PostgreSQL com backups verificados por SHA-256. Extraia o **ZIP completo** e reconstrua somente a aplicação web. Não utilize `docker compose down -v`. Verifique a navegação em Configurações e o reset numa conta de teste. O backup do ZIP original está em `HOME/backups/` do ambiente que produziu este pacote; numa instalação do usuário, faça seu próprio backup antes da substituição.

## Rollback

Restaurar os arquivos da versão anterior a partir do backup validado e reconstruir apenas o serviço web. Sem mudanças de schema e sem migrations.

## Logs

`.env` e `.env.example` incluem `ALECE_LOG_VALIDACAO=true`. Os logs da aplicação continuam sendo gerados em `src/logs/`.
