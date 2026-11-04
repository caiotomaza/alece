# Correcoes da auditoria e paginas de erro — 2026-10-24

## Escopo

- **URL canonica:** `/logs/`.
- **Evento selecionado:** `/logs/?abrir=123#log-123` expande a linha 123 na propria tabela.
- Enderecos antigos `/sistema/logs-sistema/`, `/sistema/logs-sistema/<id>/` e `/core/system-logs/` redirecionam para a rota canonica, mantendo a autorizacao.
- `Configurações > Logs`: o clique na atividade leva ao registro expandido.
- Detalhes associados visualmente a sua propria linha, inclusive em telas pequenas (rolagem horizontal apenas na tabela).
- Templates de erros **400, 403, 404, 500** com identidade visual ALECE, codigo HTTP, voltar e diagnostico.
- HTTP **503** de indisponibilidade do banco na inicializacao usa a mesma pagina visual, sem tentativa de acessar banco novamente.

## Diagnostico e seguranca

- `Copiar diagnostico`: sempre disponivel; contem apenas HTTP, identificador e caminho sem query string.
- `Copiar logs recentes` e `Baixar logs recentes`: acessam `/logs/diagnostico/`; **requerem usuario autenticado e papel de administrador**.
- Eventos recentes do PostgreSQL sao limitados aos nucleos administrados pelo usuario, ate 80 eventos.
- Trechos de `src/logs/` (ate 2 arquivos, 180 linhas e 48 KiB cada) sao restritos a **superusuarios**, pois podem misturar varios nucleos do mesmo servidor.
- A exportacao oculta padroes comuns de senhas e tokens; logs podem conter informacoes sensiveis nao identificadas, portanto nao distribua o arquivo publicamente.
- HTTP 500 pode ser renderizado mesmo com falha no banco. Se banco estiver indisponivel, endpoint de diagnostico pode nao estar acessivel; o codigo do incidente continua copiavel.
- HTTP de erro nao revela rastreamento de pilha nem variaveis de ambiente.
- Sem alteracoes no esquema do banco, migrations, regras financeiras ou ACL de logs.

## Validacao e rollback

1. Instalar em ambiente separado, com copia verificada do banco e volumes anteriores.
2. Com `ALECE_DEBUG=false` e `ALECE_LOG_VALIDACAO=true`, verificar `/logs/` e uma atividade da tela Configuracoes.
3. Confirmar pagina expandida pelo ID, acionar Detalhes/Ocultar, filtros, paginacao e rolagem responsiva.
4. Confirmar resposta 403 para contas comuns e endpoint de diagnostico (sem vazamento de logs).
5. Confirmar paginas 404 e handlers de erro no ambiente de teste; nao provocar falha 500 em producao.
6. Em caso de falha, restaurar o projeto anterior e seus arquivos do backup SHA-256 validado. Banco e dados nao precisam de migration reversa nesta entrega.

**Observação:** as rotas, regras e testes de regressao estao no codigo. A execucao Django/PostgreSQL real exige o ambiente de implantacao.
