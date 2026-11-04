# ALECE — Consistência do campo monetário do modal de renda

Data: 28/10/2026. Base exclusiva: `ALECE_COMPLETO_MODAL_RENDA_PERFIS_2026-10-28.zip`, checksum validado antes de alterar. Todos os caminhos do pacote original são preservados; mudanças isoladas de interface, testes e documentação.

## Correção

- Retirada a mensagem “Deixe em branco se a renda for desconhecida. Use zero para informar renda igual a zero.” **apenas do modal de rendas**.
- Campos passam a apresentar `R$` como prefixo visual, dentro do mesmo controle, com tokens semânticos já definidos em `alece_tokens.css` e consistência com o Design System 1.0. O prefixo tem `aria-hidden="true"` para não substituir o label do perfil; os inputs continuam identificáveis por `for`/`id` e os erros seguem associados a `aria-describedby`.
- Substituído o contorno de foco verde duplo (3 px e offset 2 px) por um indicador neutro de borda interna, contrastante nos dois temas. O foco continua perceptível por teclado.
- Modal ajusta altura ao conteúdo sem grande área vazia, limitando a altura pela viewport e mantendo rolagem interna em listas extensas.
- O valor, `name`, validação Django, permissões, CSRF e endpoint POST permaneceram inalterados. `R$` **não integra** o valor enviado: por exemplo, `2300.00` continua `2300.00` no POST. Não foi introduzida máscara monetária com alteração de formato decimal. Campos vazios continuam preservando a semântica de renda desconhecida; zero continua sendo valor informado.

## Arquivos alterados

- `src/view/templates/finance/_income_bulk_form.html`: remoção da mensagem e prefixo visual por perfil.
- `src/view/static/finance/alece_overview.css`: geometria de controle monetário reutilizando tokens, foco e altura responsiva do modal.
- `tests/ui/test_income_bulk_contract.py`: contrato estático adicional.
- `tests/browser/fixtures/income_modal_preview.html`: fixture sintética alinhada ao template.
- `scripts/quality/test_income_popup_preview.py`: verificação de prefixo, foco, erro e altura.
- `docs/visao-geral/evidencias/renda_modal_light_1280_preview.png`, `renda_modal_dark_390_preview.png`: novas capturas isoladas.

## Arquivos novos

- `scripts/quality/verify_income_currency_ui.py`: regressão isolada de 5 larguras (320/390/768/1280/1920 CSS px) × 2 temas, incluindo ausência de overflow, foco e valor do POST inalterado.
- Este relatório.

## Validação efetivamente executada

- SHA-256 do ZIP de entrada: validado; ZIP de entrada aprovado na inspeção de integridade.
- Backup anterior à edição (arquivo tar.gz) com SHA-256 próprio e verificado imediatamente, mantido no `$HOME/backups` do ambiente de edição. Registros em `$HOME/logs`.
- `pytest tests/ui/test_income_bulk_contract.py -q`: **4 aprovados**, com aviso de `pytest-django` ausente. Testes estáticos sem banco isolado real.
- `scripts/quality/test_income_popup_preview.py`: cenários claro desktop, escuro mobile, confirmação de descarte e erro HTTP 422 simulado aprovados.
- `scripts/quality/verify_income_currency_ui.py`: **10/10** combinações de viewport e tema passaram em Chromium local.
- `node --check` do JS inalterado e `compileall` dos módulos Python: concluídos sem erros sintáticos.
- As capturas são de **fixture HTML sintética** usando CSS e JavaScript reais; não representam o servidor autenticado.

**Pendente:** ambiente de homologação Django/PostgreSQL, testes HTTP reais (edição e salvamento com múltiplos perfis), inspeção de CSRF/403/409 reais, compatibilidade de teclado e leitor de tela no navegador de produção. Não há comprovação de conformidade WCAG completa.

## Atualização e rollback

1. Antes de substituir código na instalação, realizar backup validado por SHA-256 do código e `.env` e backup nativo verificável do PostgreSQL/volumes. Não sobrescrever `.env` de produção sem conferir diferenças.
2. Extrair o ZIP completo diretamente em `alece` (sem pasta raiz intermediária), atualizar **somente** o serviço `web` conforme o Compose e o procedimento operacional atual. Não remover volumes ou executar limpeza do banco.
3. Validar GET da Visão geral e POST de renda de dois perfis autorizados com valores de teste em homologação isolada, inclusive Cancelar e erro de validação. Conferir o log e a ausência de erro no servidor.
4. Em regressão, restaurar o código da versão de entrada ou do backup de arquivos, conferir SHA-256 e reconstruir apenas `web`. **Não restaurar PostgreSQL automaticamente**, porque nenhuma migration ou operação de dados foi feita neste pacote.
