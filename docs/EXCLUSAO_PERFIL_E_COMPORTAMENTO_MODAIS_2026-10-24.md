# ALECE — Exclusão lógica de perfil e comportamento uniforme dos modais

## Implementação

- **Gestão de perfis > Excluir perfil**: funcionalidade administrativa com confirmação pelo nome exato e segundo aviso explícito de operação definitiva no pop-up.
- A exclusão é **lógica**, não executa `DELETE` na tabela de perfis: os objetos financeiros, relatórios e auditorias mantêm a chave estrangeira e o identificador técnico do perfil.
- Após confirmar, o perfil recebe `deleted_at`, fica arquivado, seu nome é substituído por identificador técnico não reutilizado e as concessões de acesso são revogadas. As consultas normais e os métodos centrais de autorização passam a ignorar perfis com `deleted_at` preenchido.
- Arquivar continua sendo reversível. **Excluir** não é reversível pela interface. Uma eventual restauração exige procedimento administrativo com backup transacional e revisão de permissões.
- A edição simples não altera o estado de arquivamento, que só é mudado pelas ações explícitas arquivar e reativar.

## Comportamento de pop-ups

- Ao abrir qualquer modal gerenciado pelo controlador de UI, o scroll da página base é bloqueado, enquanto o conteúdo do modal mantém a rolagem própria.
- ESC, X e clique fora fecham o modal se não houver mudanças.
- Quando há alterações, aparece **“Deseja salvar as alterações?”**: **Não** descarta e fecha; **Sim** envia os formulários alterados, respeitando validação HTML, CSRF e autorização Django.
- A aplicação **não fecha antecipadamente** quando o servidor retorna erro ou o formulário apresenta problemas de validação.
- Se houver mais de um formulário modificado no mesmo modal, os salvamentos são **sequenciais, não atômicos**. Em caso de erro, parte pode ter sido gravada; confira as mensagens e a auditoria. A UI não promete transação multi-formulário.
- Exclusão, arquivamento, redefinição de senha e outras operações destrutivas/sensíveis **não são acionadas automaticamente** ao confirmar um fechamento. Para executá-las é necessário utilizar seus botões próprios e suas confirmações adicionais.
- Formulários continuam acessíveis pelas páginas normais quando JavaScript estiver desabilitado.

## Migração

`finance.0011_financialprofile_deleted_at` acrescenta um campo datetime opcional e indexado, com valor NULL para perfis existentes. Nenhuma linha é apagada pela migração.

## Pré-requisitos para implantação

1. Conferir volumes, `.env`, usuários administrativos e estado atual da stack.
2. Fazer **dump consistente do PostgreSQL** e backup dos arquivos de código e `.env`, validar os SHA-256; preservar os backups e logs.
3. Substituir pelo **projeto completo** e executar `docker compose up --build -d` na raiz do ALECE, somente após conferir o backup. O `docker/start.sh` executa `python manage.py check` e `python manage.py migrate --noinput` antes do Gunicorn.
4. Conferir os logs no diretório `src/logs/` com `ALECE_LOG_VALIDACAO=true`, o status do serviço e as permissões de acesso.
5. Testar arquivamento/reativação, edição de dados, confirmação de exclusão com nome incorreto, primeiro/último modal, validação de formulários e acesso negado a perfil excluído.
6. Testar rolagem e fechamento por ESC, botão X e clique no backdrop nos navegadores e resoluções-alvo.

**Nunca execute `docker compose down -v`**: pode apagar volumes financeiros persistentes.

## Rollback

Para reverter a implantação, interromper intervenções, preservar um novo dump do estado atual e restaurar **o projeto anterior e o banco compatível do mesmo ponto de recuperação**, verificando os hashes. Se não houve exclusões lógicas e nenhum dado novo foi gravado, é possível reverter `finance` para a migração `0010` antes de voltar ao código anterior, seguindo os procedimentos de change management. Reverter somente o código **depois** de excluir um perfil não recupera permissões ou campos eliminados na exibição; use o backup do banco para recuperação completa.

## Limites da validação

A compilação Python, a sintaxe JavaScript, a validação estrutural e um teste isolado do fluxo visual do navegador são executados no pacote. Os testes Django/PostgreSQL completos devem ser realizados na stack do usuário. Esta entrega não modifica dados reais do usuário.
