# ALECE — ajustes dos filtros em Despesas (23/10/2026)

## Alterações pontuais

- **Despesas imprevisíveis:** o texto visível “Mês de referência” foi retirado, mantendo um rótulo acessível a leitores de tela. O seletor de mês permanece junto ao botão `+`, ambos com altura de 42 px e distância de 8 px.
- **Histórico por período:** o seletor de categoria e o botão `Filtrar` ficam agrupados à direita do cabeçalho, com largura e altura compactas. O rótulo “Categoria” permanece junto ao seletor.
- **Aparência:** removido apenas o gradiente dos campos de mês e categoria. O fundo utiliza o mesmo tom sólido da superfície alternativa dos temas claro e escuro. O seletor de categoria mantém seta de orientação.
- **Responsividade:** em telas estreitas, o grupo de filtros preserva sua posição à direita e pode passar para a linha seguinte sem rolagem horizontal da página.

Nenhum modelo, migração, rota, permissão, política de segurança, banco ou volume Docker foi alterado.

## Log de validação do projeto

Os arquivos `.env` e `.env.example` contêm `ALECE_LOG_VALIDACAO=true`. O processo web grava um log por inicialização em `src/logs/` enquanto essa opção estiver ativa. Arquivos existentes não são apagados.

## Validação

- Sintaxe do CSS analisada sem erros com `tinycss2`.
- Código Python analisado via AST sem instalar dependências.
- Prévia estática testada no Chromium em **320, 390, 800 e 1280 px**, temas **claro e escuro**; confirmados campos de 42 px, distância de 8 px entre mês e `+`, filtros à direita, fundos sem gradiente e sem transbordamento horizontal.
- Testes de aplicação com Django, PostgreSQL e Docker: **não executados neste ambiente**.

## Implantação segura

1. Faça backup da instalação original, especialmente do `.env` personalizado, PostgreSQL, volumes Docker de arquivos e segredos, e valide os SHA-256 dos backups.
2. Extraia o ZIP completo em um diretório separado. Preserve seu `.env` de produção, se ele contiver valores diferentes; confirme `ALECE_LOG_VALIDACAO=true`.
3. Confira os arquivos e migrações antes de substituir a instalação. Não remova volumes.
4. Dentro da pasta do ALECE, reconstrua apenas a aplicação web quando estiver pronto para aplicar: `docker compose up -d --build web`.
5. Confirme as telas `/despesas/` e os registros em `src/logs/`.

**Rollback:** restaure a versão anterior dos arquivos do projeto e reconstrua apenas o serviço web. Esta revisão não exige rollback de esquema do banco de dados.

**Não execute `docker compose down -v`.**
