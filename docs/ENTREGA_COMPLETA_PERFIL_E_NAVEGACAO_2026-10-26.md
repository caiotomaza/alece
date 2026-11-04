# Correção do perfil Principal e persistência do perfil na navegação

## Origem
- Projeto base fornecido pelo usuário: `alece(4).zip`.
- Correção incorporada: ALECE_PATCH_Principal_Persistencia_Perfil_2026-10-26.zip.
- Entrega: ZIP **integral**, com arquivos diretamente na raiz (`compose.yaml`, `src/`, `docs/`, etc.), sem diretório `alece/` adicional.

## Mudanças
1. Edição administrativa do perfil Principal por formulário com destino explícito, sem mexer involuntariamente no estado de arquivamento.
2. Preferência do perfil financeiro salva na sessão Django por usuário e espaço financeiro; seleção mantida na navegação entre Visão geral, Despesas, Investimentos, Movimentações e Configurações.
3. `Todos os perfis` limpa a seleção. A preferência não concede permissões e não permite acessar perfil inativo ou não autorizado.
4. Testes de unidade e integração adicionados em `tests/finance/` e `tests/configuration/`.

## Instalação segura
Faça backup consistente do banco PostgreSQL, volumes persistentes, `.env` e arquivos existentes, valide cada SHA-256 e preserve cópia para rollback.
Com o serviço interrompido ou em janela controlada, **extraia o conteúdo do ZIP dentro da pasta raiz existente `alece` e substitua os arquivos**. O ZIP não cria diretório adicional.
No diretório `alece`, recrie somente a aplicação web conforme seu ambiente Docker (`docker compose up -d --build --no-deps web`), depois verifique logs, `/saude/pronto/`, edição do perfil Principal e seleção entre páginas.
A extração não remove arquivos obsoletos de entregas anteriores. Para esta alteração não existem arquivos a excluir.

## Rollback
Restaure os arquivos anteriores da versão `alece(4).zip` e, se necessário, os backups validados de banco/volumes; reconstrua a imagem web. Não execute `docker compose down -v`.

## Validação desta entrega
O empacotamento, hashes do manifesto, compilação Python e testes unitários puros são verificados localmente. Os testes integrados Django/PostgreSQL só podem ser comprovados em um ambiente que execute essa stack.
