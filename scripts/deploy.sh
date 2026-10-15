#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Deploy controlado: sem rollback destrutivo automático.
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
for cmd in docker sha256sum date hostname tee; do
  command -v "$cmd" >/dev/null || { echo "Ausente: $cmd" >&2; exit 1; }
done
[[ -f .env ]] || { echo 'Crie .env usando scripts/bootstrap.sh.' >&2; exit 1; }
mkdir -p "$HOME/logs" "$HOME/backups"
TS=$(date '+%Y-%m-%d_%H-%M-%S')
LOG="$HOME/logs/${TS}.log"
BACKUP="$HOME/backups/${TS}__alece-postgresql.dump"
[[ ! -e "$LOG" && ! -e "$BACKUP" ]] || { echo 'Timestamp já utilizado. Tente após um segundo.' >&2; exit 1; }
exec > >(tee -a "$LOG") 2>&1
trap 'code=$?; echo "[ERROR] deploy interrompido exit=$code; logs/backup preservados. Consulte RUNBOOK.md para rollback. backup=$BACKUP"; exit "$code"' ERR
echo "[START] $(date --iso-8601=seconds) host=$(hostname) user=$(id -un) pwd=$PWD"
docker compose --env-file .env version
docker compose --env-file .env config --quiet
echo '[CHECK] Subindo somente db (web existente ainda não foi alterado).'
docker compose --env-file .env up -d db
echo '[BACKUP] Dump PostgreSQL antes de migration ou atualização web.'
docker compose --env-file .env exec -T db sh -ec 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null'
docker compose --env-file .env exec -T db sh -ec 'exec pg_dump -Fc -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > "${BACKUP}.partial"
[[ -s "${BACKUP}.partial" ]] || { echo 'Falha: dump vazio' >&2; exit 1; }
docker compose --env-file .env exec -T db pg_restore -l < "${BACKUP}.partial" >/dev/null
mv -- "${BACKUP}.partial" "$BACKUP"
( cd "$HOME/backups" && sha256sum "$(basename "$BACKUP")" > "$(basename "$BACKUP").sha256" && sha256sum -c "$(basename "$BACKUP").sha256" )
echo '[BUILD] Construindo imagem web. Não publica no registro.'
docker compose --env-file .env build web
echo '[CHECK] Checagem Django pré-migração.'
docker compose --env-file .env run --rm -T --no-deps web python manage.py check
echo '[MIGRATION] Aplicando alterações versionadas no banco.'
docker compose --env-file .env run --rm -T --no-deps web python manage.py migrate --noinput
echo '[DEPLOY] Iniciando/atualizando web.'
docker compose --env-file .env up -d --no-build web
# Testa dentro do contêiner para não assumir IP, porta ou software de curl no host.
echo '[HEALTH] Testando /health/ready/ pela rede interna do contêiner.'
docker compose --env-file .env exec -T web python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/health/ready/', timeout=8); assert r.status == 200"
docker compose --env-file .env ps
echo "[OK] Implantação e readiness checados. Backup=${BACKUP}; log=${LOG}"
