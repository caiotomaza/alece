# ALECE — Implantação controlada e reversão

1. Preservar código corrente e estado do PostgreSQL/volumes produtivos com backup nativo íntegro, SHA-256 validado e registro em `$HOME/logs`. Não publicar `.env`, tokens, dumps ou logs sensíveis no GitHub.
2. Conferir checksum SHA-256 do ZIP entregue. Extrair **diretamente** na pasta `alece`, preservando o `.env` real após comparar alterações de exemplo. Não extrair por cima da instalação de produção sem procedimento de janela e plano de acesso.
3. Atualizar estáticos com mecanismo oficial do deploy (`collectstatic` em imagem/release, se aplicável) e reavaliar logs. Não há migrations nem alteração no esquema.
4. No ambiente **isolado**, executar `python manage.py check`, `makemigrations --check --dry-run`, testes Django e suíte de navegador, com banco efêmero; o job de performance é manual. Validar ao menos uma navegação real nos cinco destinos, dois temas, mobile/desktop, cálculo, registros e estorno.
5. Em falha, restaurar ZIP de origem validado e estáticos associados; como não houve mudança de schema, não executar rollback automático do banco. Reavaliar registros produzidos após implantação antes de cogitar restauração de dados.
6. Preservar todos os artefatos/logs e backups em HOME, incluindo checksums. Não habilitar DEBUG em produção nem registrar SQL com parâmetros financeiros.

**Riscos residuais:** código ORM de prefetch ainda depende de teste PostgreSQL real; runner CI de desempenho não executado neste ambiente; ausência de comparação temporal em aplicação viva. Não declarar ganhos de performance ou aprovação em produção até evidências integradas.
