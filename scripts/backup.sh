#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
for cmd in docker sha256sum date hostname tee; do
  command -v "$cmd" >/dev/null || { echo "Ausente: $cmd" >&2; exit 1; }
done
[[ -f .env ]] || { echo 'Arquivo .env não existe; use bootstrap.sh primeiro.' >&2; exit 1; }
mkdir -p "$HOME/logs" "$HOME/backups"
TS=$(date '+%Y-%m-%d_%H-%M-%S')
LOG="$HOME/logs/${TS}.log"
ARCHIVE="$HOME/backups/${TS}__alece-postgresql.dump"
[[ ! -e "$LOG" && ! -e "$ARCHIVE" ]] || { echo 'Timestamp já usado. Tente novamente após um segundo.' >&2; exit 1; }
exec > >(tee -a "$LOG") 2>&1
trap 'code=$?; echo "[ERRO] Backup falhou exit=${code}. Artefatos parciais não foram removidos: ${ARCHIVE}.partial"; exit "$code"' ERR
echo "[START] $(date --iso-8601=seconds) host=$(hostname) user=$(id -un) backup=${ARCHIVE}"
docker compose --env-file .env config --quiet
docker compose --env-file .env exec -T db sh -ec 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null'
docker compose --env-file .env exec -T db sh -ec 'exec pg_dump -Fc -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > "${ARCHIVE}.partial"
[[ -s "${ARCHIVE}.partial" ]] || { echo 'Dump vazio' >&2; exit 1; }
# pg_restore lista o índice e detecta dumps truncados em boa parte dos casos.
docker compose --env-file .env exec -T db pg_restore -l < "${ARCHIVE}.partial" >/dev/null
mv -- "${ARCHIVE}.partial" "$ARCHIVE"
( cd "$HOME/backups" && sha256sum "$(basename "$ARCHIVE")" > "$(basename "$ARCHIVE").sha256" && sha256sum -c "$(basename "$ARCHIVE").sha256" )
echo "[OK] Dump criado, listado e SHA-256 validado. log=${LOG}"
