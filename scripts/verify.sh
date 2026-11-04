#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
for cmd in python3 date hostname tee; do command -v "$cmd" >/dev/null || { echo "Ausente: $cmd" >&2; exit 1; }; done
mkdir -p "$HOME/logs"
LOG="$HOME/logs/$(date '+%Y-%m-%d_%H-%M-%S').log"
[[ ! -e "$LOG" ]] || { echo 'Log já existente; tente depois de um segundo.' >&2; exit 1; }
exec > >(tee -a "$LOG") 2>&1
trap 'code=$?; echo "[ERROR] preflight falhou exit=$code"; exit "$code"' ERR
echo "[START] $(date --iso-8601=seconds) host=$(hostname)"
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PYCODE'
from ast import parse
from pathlib import Path
files = [Path('manage.py'), *Path('src').rglob('*.py'), *Path('tests').rglob('*.py')]
for file in files:
    parse(file.read_text(encoding='utf-8'), filename=str(file))
print(f'Sintaxe Python OK: {len(files)} arquivos')
PYCODE
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/controller:. python3 -m unittest tests.finance.test_calculations -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/controller:. python3 -m unittest tests.operations.test_repository_architecture_static tests.operations.test_repository_structure tests.ui.test_navigation_structure tests.ui.test_ui_visual_structure -v
if command -v docker >/dev/null; then docker compose config --quiet; fi
echo "[OK] Validação estática + domínio sem dependências. log=${LOG}"
