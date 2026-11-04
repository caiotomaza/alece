#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-only
set -eu
cd /app
# Falhe com uma mensagem objetiva antes de rodar migracoes.
# Nunca imprima segredos no stdout/stderr.
python - <<'PY_CHECK_SECRETS'
import os
from pathlib import Path

for name in ('ALECE_SECRET_KEY', 'ALECE_DB_PASSWORD'):
    value = os.environ.get(name, '').strip()
    if not value:
        filename = os.environ.get(name + '_FILE', '').strip()
        if not filename:
            raise SystemExit('ALECE: falta ' + name + ' e ' + name + '_FILE.')
        source = Path(filename)
        try:
            value = source.read_text(encoding='utf-8').strip()
        except OSError as error:
            raise SystemExit('ALECE: impossivel ler ' + name + '_FILE: ' + type(error).__name__)
    if not value or value.startswith('CHANGE_ME'):
        raise SystemExit('ALECE: segredo invalido em ' + name + '.')
print('ALECE: segredos obrigatorios acessiveis (valores ocultos).')
PY_CHECK_SECRETS
python manage.py check
python manage.py migrate --noinput
# Verificações pós-migração, somente leitura e falha explícita.
python manage.py migrate --check --noinput
python manage.py alece_startup_check
# Evite registrar query string, Referer, cookies e cabeçalhos sensíveis.
exec gunicorn --bind 0.0.0.0:8000 --workers 2 --access-logfile - --error-logfile - \
  --access-logformat '%(h)s %(t)s "%(m)s %(U)s %(H)s" %(s)s %(b)s' \
  config.wsgi:application
