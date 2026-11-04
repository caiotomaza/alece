# ALECE — diagnóstico do loop de inicialização (2026-10-23)

## Evidências nos logs originais

- Banco `db` inicia com saúde `Healthy`.
- `web` inicia Gunicorn, que falha ao carregar `config.settings` por `ALECE_SECRET_KEY` ausente.
- Log aponta `settings.py:26`, mas neste pacote o `RuntimeError` está em `settings.py:37` na versão original recebida.
- Neste pacote, `docker/start.sh` executava `python manage.py migrate` **antes** do Gunicorn. O log recebido mostrou Gunicorn sem essa etapa de bootstrap.

**Diagnóstico mais provável:** o Compose reaproveitou imagem `alece-web` gerada de versão anterior. O comando original sugerido `docker compose up` não assegurava recompilação depois de substituir os fontes.

## Ajustes desta revisão

1. Em `compose.yaml`, `web.pull_policy: build` obriga reconstrução da imagem conforme especificação oficial Compose.
2. `docker/start.sh` verifica existência e leitura de segredos via `_FILE` antes de iniciar Django, sem expor valores, e executa `manage.py check` antes das migrações.
3. No README, a execução inicial indica `docker compose up --build -d`.
4. Para o Windows, `scripts/TECH_ALECE_Corrigir_Loop_Startup.ps1` faz pré-verificações, backup com SHA-256 de configuração, volumes de secrets/media existentes, dump consistente do PostgreSQL existente, e recria **somente** o web após build.

## Como executar no Windows

1. Salve cópia do diretório da instalação anterior. Extraia este ZIP em outro diretório ou atualize apenas os arquivos com alterações. **Não substitua o `.env` personalizado** por um modelo.
2. Verifique Docker Desktop e a versão do Compose. Abra PowerShell no diretório ALECE atualizado.
3. Rode `powershell.exe -NoProfile -File .\scripts\TECH_ALECE_Corrigir_Loop_Startup.ps1`.
4. Confirme o log `HOME/logs/YYYY-MM-DD_HH-MM-SS.log`, as verificações SHA-256 em `HOME/backups/` e a saúde do serviço `web`.

**Rollback:** preserve o ZIP original e os backups datados da configuração, segredos, mídia e dump PostgreSQL. O retorno a versões anteriores do banco exige restaurar o dump **em ambiente isolado e testado** antes de restaurar o serviço; nunca execute `down -v` nem substitua os secrets por novos valores. Se somente a imagem foi alterada e o schema do banco permaneceu igual, reconstrua a versão anterior usando os arquivos originais e a mesma stack/volumes. A versão anterior pode continuar falhando pela chave ausente.

**Validação neste ambiente:** sintaxe shell, estrutura Compose e compilação Python; teste real Docker Desktop e banco ainda requerem execução no host do usuário. Não foi declarada aprovação funcional sem teste.
