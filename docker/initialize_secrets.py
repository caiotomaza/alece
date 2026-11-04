# SPDX-License-Identifier: GPL-3.0-only
"""Docker one-shot initializer: keep credentials stable in a named volume."""
import os
from pathlib import Path
from secrets import token_urlsafe

root = Path('/run/alece-secrets')
root.mkdir(mode=0o755, parents=True, exist_ok=True)
for name, length in [('secret_key', 48), ('db_password', 36)]:
    dest = root / name
    try:
        fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        if not dest.is_file() or not dest.read_text(encoding='utf-8').strip():
            raise RuntimeError(f'Existing secret is missing or invalid: {name}')
        continue
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        stream.write(token_urlsafe(length))
        stream.flush()
        os.fsync(stream.fileno())
print('ALECE: secret files ready (values not displayed).')
