# Importação por arrastar, soltar ou escolher arquivo

## Funcionalidade
A página **Movimentações** apresenta uma área de seleção de um arquivo CSV, OFX ou PDF.
Clique na área, escolha o arquivo ou arraste-o do gerenciador de arquivos. Em navegadores
com JavaScript, o envio multipart é iniciado automaticamente sem botão. O fluxo usa
o endpoint Django existente `finance:import-upload`, autorização de edição de contas
e movimentações, proteção CSRF e limite de 5 MiB/5.000 linhas.

Depois do upload e da análise, a aplicação redireciona à **prévia editável**,
conforme o comportamento anterior. **Nenhum lançamento financeiro é confirmado**
até a ação explícita do usuário na tela de revisão. Não há envio automático a APIs de IA.

O estado de processamento é textual e não inventa porcentagem de progresso; erros de
formato/tamanho são mostrados antes do envio. Sem JavaScript, aparece um botão de
fallback para preservar o envio de arquivos.

## Teste
1. Em `/movimentacoes/`, arraste um CSV/OFX/PDF pequeno para a área; confira o
   estado de processamento e o redirecionamento à prévia.
2. Volte e teste por clique e seletor do sistema, com arquivo de até 5 MiB.
3. Teste arquivo sem extensão permitida, vazio, maior que 5 MiB e soltura de dois arquivos.
4. Revise registros importados; confirme que nenhum lançamento foi gravado no ledger
   antes do botão explícito de confirmação da prévia.
5. Confira em celular e em temas claro/escuro. Reavalie no servidor Docker real.

## Atualização e rollback
Faça dump consistente de PostgreSQL e backup dos volumes e do `.env` atual antes de
substituir o projeto. Valide SHA-256 dos backups; preserve a instalação anterior para
rollback. Reconstrua somente o serviço web sem remover volumes (`down -v` é proibido).
A alteração não adiciona migrações. Para reverter, restaure os quatro arquivos
registrados no backup anterior da intervenção e reconstrua o serviço web, mantendo
os volumes. Os logs continuam em `src/logs/` quando `ALECE_LOG_VALIDACAO=true`.
