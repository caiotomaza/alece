# SPDX-License-Identifier: GPL-3.0-only
"""Volume-backed API tokens; never expose secrets in models, logs, or templates."""
import os
import re
import tempfile
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

SECRET_DIR = Path(os.getenv("ALECE_AI_SECRET_DIR", "/app/private/ai"))


def _path(pk):
    if not isinstance(pk, int) or pk <= 0:
        raise ValueError("Identificador de integração inválido")
    return SECRET_DIR / f"provider-{pk}.key"


def has_token(pk):
    return _path(pk).is_file()


def read_token(pk):
    path = _path(pk)
    if not path.is_file():
        return ""
    if path.is_symlink():
        raise ImproperlyConfigured("Chave de API inválida")
    return path.read_text(encoding="utf-8").strip()


def write_token(pk, value):
    value = value.strip()
    if not value or len(value) > 4096 or any(ch in value for ch in "\r\n\x00"):
        raise ValueError("A chave de API informada é inválida")
    SECRET_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    if SECRET_DIR.is_symlink():
        raise ImproperlyConfigured("Diretório de chaves inválido")
    os.chmod(SECRET_DIR, 0o700)
    name = None
    try:
        with tempfile.NamedTemporaryFile(dir=SECRET_DIR, prefix=".token-", mode="w", encoding="utf-8", delete=False) as stream:
            name = stream.name
            os.fchmod(stream.fileno(), 0o600)
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        target = _path(pk)
        if target.is_symlink():
            raise ImproperlyConfigured("Destino de chave inválido")
        os.replace(name, target)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def delete_token(pk):
    """Revoga a chave local sem expor seu conteúdo. Nunca segue symlinks."""
    target = _path(pk)
    if SECRET_DIR.is_symlink() or target.is_symlink():
        raise ImproperlyConfigured("Armazenamento de chaves inválido")
    try:
        target.unlink()
    except FileNotFoundError:
        return False
    return True
