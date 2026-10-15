#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
for cmd in bash python3 docker sha256sum date hostname tee; do
  command -v "$cmd" >/dev/null || { printf 'Pré-requisito ausente: %s\n' "$cmd" >&2; exit 1; }
done
if ! docker compose version >/dev/null 2>&1; then echo 'Docker Compose v2 não disponível' >&2; exit 1; fi
mkdir -p "$HOME/logs" "$HOME/backups"
LOG="$HOME/logs/$(date '+%Y-%m-%d_%H-%M-%S').log"
if [[ -e "$LOG" ]]; then echo 'Log já existe; tente novamente após um segundo.' >&2; exit 1; fi
exec > >(tee -a "$LOG") 2>&1
trap 'status=$?; echo "[ERROR] linha ${LINENO}; exit=${status}; log=${LOG}"; exit "$status"' ERR
echo "[START] $(date --iso-8601=seconds) host=$(hostname) user=$(id -un) pwd=$PWD"
echo 'Pré-verificação: Docker Compose detectado; .env ainda não foi alterado.'
if [[ -f .env ]]; then
  echo 'Arquivo .env já existe; nenhuma alteração foi feita.'
  docker compose --env-file .env config --quiet
  echo '[OK] configuração Compose válida; não imprime secrets.'
  exit 0
fi
if [[ ! -f .env.example ]]; then echo 'Falta .env.example' >&2; exit 1; fi
python3 - <<'PYENV'
import os
from pathlib import Path
from secrets import token_urlsafe

original = Path('.env.example').read_text(encoding='utf-8')
content = original.replace('CHANGE_ME_GENERATE_RANDOM_SECRET', token_urlsafe(48))
content = content.replace('CHANGE_ME_GENERATE_RANDOM_PASSWORD', token_urlsafe(36))
path = Path('.env')
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w', encoding='utf-8') as stream:
    stream.write(content)
PYENV
if ! docker compose --env-file .env config --quiet; then
  echo 'Configuração Compose inválida. Arquivo .env permanece para inspeção manual.' >&2
  exit 1
fi
echo '[OK] arquivo .env criado com modo 600 e segredos aleatórios; confirme bind/ALLOWED_HOSTS antes de implantar.'
echo "Log: ${LOG}"
