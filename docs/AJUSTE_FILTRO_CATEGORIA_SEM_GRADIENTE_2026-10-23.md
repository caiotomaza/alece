# Ajuste do filtro de categoria

Nesta revisão, somente o filtro **Categoria** e o botão **Filtrar** de
**Despesas → Histórico por período** passaram a utilizar fundos sólidos.
Foram preservados os tamanhos, cantos, posição à direita, opções, cores do tema
claro e escuro e o ícone de seta do seletor.

## Causa

O arquivo `alece_ui_consistency.css` utiliza um gradiente global para selects
com `background-image` e `!important`. Por ser carregado após `alece.css`, esse
estilo substituía o fundo sólido específico definido para o histórico. O ajuste
é localizado e aparece depois dos controles globais para evitar regressões.

## Implantação e rollback

Antes de substituir a instalação atual, faça backup dos dados PostgreSQL, dos
volumes Docker, do `.env` instalado e do projeto; valide o SHA-256. A correção
não envolve migrations ou alterações de dados. Reconstrua somente o serviço web
sem remover volumes. Para desfazer este ajuste específico, restaure o arquivo
`src/view/static/finance/alece_ui_consistency.css` a partir do backup de CSS
validado em `HOME/backups/`, reconstruindo o serviço web depois.

`ALECE_LOG_VALIDACAO=true` continua configurado em `.env` e `.env.example`;
os logs da aplicação continuam em `src/logs/`.
