#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Run ALECE with optional per-startup stdout/stderr capture.

The original combined output still goes to Docker logs. Log creation is atomic
and exclusive, and child exit/signal status is propagated to the container.
No application secrets are read or printed here.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time


ENABLED_VALUES = frozenset({'1', 'true', 'yes', 'on'})
LOG_DIR = Path(__file__).resolve().parents[1] / 'src' / 'logs'


def enabled(value: str) -> bool:
    return value.strip().lower() in ENABLED_VALUES


def open_execution_log(folder: Path):
    """Reserve one UTC timestamp-named log without overwriting an older run."""
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    deadline = time.monotonic() + 10
    while True:
        stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d_%H-%M-%S')
        path = folder / (stamp + '.log')
        try:
            fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            return path, os.fdopen(fd, 'wb', buffering=0)
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise RuntimeError('Impossível reservar nome exclusivo para log de inicialização.')
            time.sleep(0.2)


def _forward_signal(child: subprocess.Popen, sig: int):
    if child.poll() is not None:
        return
    try:
        # Child starts a separate session; forward to Gunicorn and any workers.
        os.killpg(child.pid, sig)
    except ProcessLookupError:
        pass


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit('Comando de inicialização ausente.')
    if not enabled(os.getenv('ALECE_LOG_VALIDACAO', 'false')):
        # Keep original PID 1 and signal handling when disk logging is off.
        os.execvp(argv[0], argv)

    try:
        path, log = open_execution_log(LOG_DIR)
    except OSError as exc:
        raise SystemExit('ALECE: não foi possível criar log em src/logs/. '
                         'Verifique as permissões de escrita do volume: '
                         + type(exc).__name__) from None

    with log:
        start = datetime.now(timezone.utc).isoformat(timespec='seconds')
        info = (
            f'ALECE_LOG_VALIDACAO=true | inicio_utc={start} | '
            f'host={socket.gethostname()} | uid={os.getuid()} | '
            f'launcher_pid={os.getpid()} | arquivo={path.name}\n'
        )
        log.write(info.encode('utf-8'))
        sys.stdout.write(info)
        sys.stdout.flush()

        child = None
        previous_handlers = {}
        try:
            child = subprocess.Popen(
                argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                start_new_session=True, bufsize=0,
            )
            for signum in (signal.SIGTERM, signal.SIGINT):
                previous_handlers[signum] = signal.getsignal(signum)
                signal.signal(signum, lambda sig, _frame: _forward_signal(child, sig))

            assert child.stdout is not None
            while True:
                data = os.read(child.stdout.fileno(), 65536)
                if not data:
                    break
                log.write(data)
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
            result = child.wait()
            status = f'ALECE: fim_utc={datetime.now(timezone.utc).isoformat(timespec="seconds")} codigo_saida={result}\n'
            log.write(status.encode('utf-8'))
            sys.stdout.write(status)
            sys.stdout.flush()
            return 128 - result if result < 0 else result
        except BaseException as exc:
            status = f'ALECE: erro no capturador: {type(exc).__name__}\n'
            log.write(status.encode('utf-8'))
            sys.stderr.write(status)
            if child is not None and child.poll() is None:
                _forward_signal(child, signal.SIGTERM)
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    _forward_signal(child, signal.SIGKILL)
                    child.wait()
            raise
        finally:
            for signum, previous in previous_handlers.items():
                signal.signal(signum, previous)


if __name__ == '__main__':
    sys.exit(main())
