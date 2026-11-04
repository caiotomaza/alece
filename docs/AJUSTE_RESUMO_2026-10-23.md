# Ajuste visual do cabeçalho Resumo — 2026-10-23

## Motivo
A regra genérica `.section-head` aplica margem superior mesmo quando o título
já fica dentro do cartão Resumo, provocando uma distância superior maior que
em Metas.

## Alteração
- Removido o texto decorativo "Renda como base da distribuição".
- `#overview-summary-card > .section-head`: `margin: 0 0 16px`, reduzido para
  14px em telas até 700px, seguindo a mesma lógica do cartão Metas.
- CSS adicionado ao final de `alece_ui_consistency.css`, carregado após
  `alece.css`, com especificidade do ID do cartão para evitar regressões.

## Escopo e segurança
Somente HTML de apresentação e CSS foram modificados. Nenhuma migração,
permissão, regra financeira ou configuração do banco foi alterada.

## Implantação
Faça backup validado do PostgreSQL, volumes e das configurações locais antes de
substituir a instalação. Não execute `docker compose down -v`.
Reconstrua a aplicação segundo o RUNBOOK e valide o alinhamento nas larguras
móvel e desktop, em ambos os temas.

## Rollback
Restaure o projeto e os arquivos de configuração do backup anterior e reconstrua
somente o serviço web. Alterações de banco não são necessárias.
