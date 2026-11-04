#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Validate ALECE's actual Docker startup and isolated PostgreSQL lifecycle.

Requires local Docker Compose >=2.24; never targets the production Compose stack.
"""

import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / ".env.example"
VALIDATION = ROOT / "compose.validation.yaml"
AUDIT = ROOT / "compose.audit.yaml"

# This marker is required INSIDE the validated container before any SQL write.
PROBE = """
import os
import django
django.setup()
from django.conf import settings
from django.db import connection
assert os.environ.get('ALECE_VALIDATION_ONLY') == '1'
assert os.environ.get('ALECE_TEST_ISOLATED') == '1'
assert settings.DATABASES['default']['NAME'] == 'alece_audit'
assert settings.DATABASES['default']['USER'] == 'alece_audit'
assert settings.DATABASES['default']['HOST'] == 'db'
assert settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql'
assert os.environ.get('ALECE_LOG_LEVEL') == 'INFO'
assert os.environ.get('ALECE_SECRET_KEY_FILE') == '/run/alece-secrets/secret_key'
assert os.environ.get('ALECE_DB_PASSWORD_FILE') == '/run/alece-secrets/db_password'
assert not os.environ.get('ALECE_SECRET_KEY')
assert not os.environ.get('ALECE_DB_PASSWORD')
with connection.cursor() as cursor:
    cursor.execute('SELECT current_database(), current_user')
    assert cursor.fetchone() == ('alece_audit', 'alece_audit')
    cursor.execute('CREATE TABLE IF NOT EXISTS alece_validation_probe (marker varchar(64) PRIMARY KEY)')
    if os.environ.get('ALECE_VALIDATION_ACTION') == 'write':
        cursor.execute('INSERT INTO alece_validation_probe (marker) VALUES (%s) ON CONFLICT DO NOTHING',
                       [os.environ['ALECE_VALIDATION_MARKER']])
    cursor.execute('SELECT COUNT(*) FROM alece_validation_probe WHERE marker = %s',
                   [os.environ['ALECE_VALIDATION_MARKER']])
    assert cursor.fetchone()[0] == 1
import urllib.request
response = urllib.request.urlopen('http://127.0.0.1:8000/saude/pronto/', timeout=8)
assert response.status == 200
"""

SECRET_FINGERPRINT = """
import hashlib
from pathlib import Path
from os import environ
assert environ.get('ALECE_VALIDATION_ONLY') == '1'
for path in ('/run/alece-secrets/secret_key', '/run/alece-secrets/db_password'):
    print(hashlib.sha256(Path(path).read_bytes()).hexdigest())
"""


class ValidationError(RuntimeError):
    pass


def safe_environment():
    """Do not inherit ALECE/Compose overrides from the operator's shell."""
    return {key: value for key, value in os.environ.items()
            if not key.startswith(("ALECE_", "COMPOSE_"))}


def command(args, *, env, input_text=None, quiet=False, cwd=ROOT):
    result = subprocess.run(args, cwd=cwd, env=env, text=True, input=input_text,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
                            timeout=1800)
    if result.returncode:
        raise ValidationError(f"Comando falhou (exit={result.returncode}): "
                              + " ".join(str(arg) for arg in args[:8])
                              + ". Consulte a saída do Docker no terminal local.")
    return result.stdout.strip() if not quiet else ""


def compose(name, file, *, env, args, quiet=False):
    return command(["docker", "compose", "--env-file", str(EXAMPLE),
                    "-p", name, "-f", str(file), *args], env=env, quiet=quiet)


def check_local_docker(env):
    if not shutil.which("docker"):
        raise ValidationError("Docker CLI indisponível; validação integrada NÃO EXECUTADA.")
    host = env.get("DOCKER_HOST", "")
    if host and not host.startswith(("unix://", "npipe://")):
        raise ValidationError("DOCKER_HOST aponta para ambiente remoto ou desconhecido.")
    version = command(["docker", "compose", "version", "--short"], env=env)
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match or tuple(map(int, match.groups())) < (2, 24, 0):
        raise ValidationError("É necessário Docker Compose 2.24+.")
    endpoint = command(["docker", "context", "inspect", "--format",
                        "{{json .Endpoints.docker.Host}}"], env=env)
    try:
        endpoint = json.loads(endpoint)
    except (ValueError, TypeError) as exc:
        raise ValidationError("Não foi possível verificar o contexto Docker local.") from exc
    if not isinstance(endpoint, str) or not endpoint.startswith(("unix://", "npipe://")):
        raise ValidationError("Contexto Docker remoto ou desconhecido: operação bloqueada.")
    command(["docker", "info", "--format", "{{.ServerVersion}}"], env=env, quiet=True)


def assert_config_isolated(payload):
    data = json.loads(payload)
    if not data.get("name", "").startswith("alece_val_isolado_"):
        raise ValidationError("Namespace Compose de validação ausente.")
    networks = data.get("networks", {})
    if not networks or any(not network.get("internal", False) for network in networks.values()):
        raise ValidationError("Rede de validação deve ser interna.")
    for name, detail in data.get("volumes", {}).items():
        volume_name = detail.get("name", "")
        if detail.get("external") or not volume_name.startswith(data["name"] + "_"):
            raise ValidationError(f"Volume não isolado: {name}")
    for name, service in data.get("services", {}).items():
        for forbidden in ("container_name", "ports", "network_mode", "privileged", "devices", "pid"):
            if service.get(forbidden):
                raise ValidationError(f"Propriedade perigosa em {name}: {forbidden}")
        for volume in service.get("volumes", []):
            if volume.get("type") == "bind":
                source = Path(volume.get("source", "")).resolve()
                if (name != "secrets-init" or source != (ROOT / "docker/initialize_secrets.py").resolve()
                        or not volume.get("read_only", False)):
                    raise ValidationError(f"Bind mount não autorizado no serviço {name}.")
    web = data.get("services", {}).get("web", {})
    expected = {"ALECE_VALIDATION_ONLY": "1", "ALECE_DB_NAME": "alece_audit",
                "ALECE_DB_USER": "alece_audit", "ALECE_DB_HOST": "db"}
    for key, value in expected.items():
        if str(web.get("environment", {}).get(key)) != value:
            raise ValidationError(f"Variável de isolamento divergente: {key}")
    return True


def check_env_layering(env):
    """Check the real compose.yaml with and without optional .env, config only."""
    with tempfile.TemporaryDirectory(prefix="alece-config-check-") as directory:
        temp = Path(directory)
        shutil.copyfile(ROOT / "compose.yaml", temp / "compose.yaml")
        shutil.copyfile(EXAMPLE, temp / ".env.example")
        def parse():
            raw = command(["docker", "compose",
                           "-p", "alece_config_check", "-f", str(temp / "compose.yaml"),
                           "config", "--format", "json"], env=env, cwd=temp)
            return json.loads(raw)
        without = parse()
        service = without["services"]["web"]
        if service["environment"].get("ALECE_LOG_LEVEL") != "INFO":
            raise ValidationError("Padrão de env_file não chegou ao web.")
        if str(service["ports"][0]["published"]) != "8088":
            raise ValidationError("Interpolação de porta sem .env divergente.")
        # A .env temporária contém SOMENTE valores de teste, jamais segredos reais.
        (temp / ".env").write_text("ALECE_LOG_LEVEL=WARNING\nALECE_PORT=18088\n", encoding="utf-8")
        with_override = parse()["services"]["web"]
        if with_override["environment"].get("ALECE_LOG_LEVEL") != "WARNING":
            raise ValidationError("Sobreposição de env_file opcional não funciona.")
        if str(with_override["ports"][0]["published"]) != "18088":
            raise ValidationError("Interpolação de porta com .env divergente.")


def wait_healthy(name, file, env):
    container_id = compose(name, file, env=env, args=["ps", "-q", "web"])
    if not container_id or "\n" in container_id:
        raise ValidationError("Não foi possível identificar o web isolado.")
    for _ in range(60):
        state = command(["docker", "inspect", "--format", "{{.State.Health.Status}}",
                         container_id], env=env)
        if state == "healthy":
            return
        if state == "unhealthy":
            raise ValidationError("Healthcheck do Django falhou.")
        time.sleep(3)
    raise ValidationError("Healthcheck não concluiu no limite de verificação.")


def verification(name, file, env, marker, action):
    args = ["exec", "-T", "-e", f"ALECE_VALIDATION_MARKER={marker}",
            "-e", f"ALECE_VALIDATION_ACTION={action}", "web", "python", "-c", PROBE]
    compose(name, file, env=env, args=args, quiet=True)
    return compose(name, file, env=env, args=["exec", "-T", "web", "python", "-c",
                                               SECRET_FINGERPRINT])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-suite", action="store_true",
                        help="Valida apenas Compose, inicialização e persistência; não executa pytest")
    args = parser.parse_args()
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    name = "alece_val_isolado_" + secrets.token_hex(5)
    qa_name = name + "_qa"
    marker = secrets.token_hex(16)
    env = safe_environment()
    output = Path.home() / "test-results" / name
    output.mkdir(parents=True, exist_ok=False)
    report = {"timestamp": stamp, "validation_project": name, "audit_project": qa_name,
              "results": {"preflight": "NAO_EXECUTADO", "compose": "NAO_EXECUTADO",
                          "web": "NAO_EXECUTADO",
                          "persistence": "NAO_EXECUTADO", "django": "NAO_EXECUTADO",
                          "audit_suite": "NAO_EXECUTADO",
                          "browser": "NAO_EXECUTADO",
                          "browser_lock": "NAO_EXECUTADO"}}
    started = False
    qa_started = False
    stage = "preflight"
    try:
        check_local_docker(env)
        report["results"]["preflight"] = "APROVADO"
        stage = "compose"
        check_env_layering(env)
        validation_payload = compose(name, VALIDATION, env=env,
                                     args=["config", "--format", "json"])
        assert_config_isolated(validation_payload)
        compose(name, VALIDATION, env=env, args=["config", "--quiet"], quiet=True)
        report["results"]["compose"] = "APROVADO"
        print("[OK] Compose: interpolação, env_file e isolamento verificados.", flush=True)
        started = True
        stage = "web"
        compose(name, VALIDATION, env=env, args=["up", "--build", "-d"], quiet=True)
        wait_healthy(name, VALIDATION, env)
        report["results"]["web"] = "APROVADO"
        print("[OK] Aplicação real: build, migração e healthcheck concluídos.", flush=True)
        stage = "django"
        before = verification(name, VALIDATION, env, marker, "write")
        for step in (["check"], ["makemigrations", "--check", "--dry-run"],
                     ["migrate", "--check", "--noinput"]):
            compose(name, VALIDATION, env=env,
                    args=["exec", "-T", "web", "python", "manage.py", *step], quiet=True)
        report["results"]["django"] = "APROVADO"
        print("[OK] Django: configurações, migrações e banco de teste verificados.", flush=True)
        stage = "persistence"
        compose(name, VALIDATION, env=env, args=["down"], quiet=True)
        compose(name, VALIDATION, env=env, args=["up", "--no-build", "-d"], quiet=True)
        wait_healthy(name, VALIDATION, env)
        after = verification(name, VALIDATION, env, marker, "read")
        if before != after:
            raise ValidationError("Segredos foram alterados durante a reinicialização.")
        report["results"]["persistence"] = "APROVADO"
        print("[OK] Ciclo down/up: registro sintético e segredos persistiram.", flush=True)
        if not args.skip_suite:
            stage = "audit_suite"
            qa_started = True
            compose(qa_name, AUDIT, env=env, args=["config", "--quiet"], quiet=True)
            compose(qa_name, AUDIT, env=env,
                    args=["up", "--build", "--abort-on-container-exit", "--exit-code-from", "tests"],
                    quiet=True)
            report["results"]["audit_suite"] = "APROVADO"
            print("[OK] Suíte Django/PostgreSQL isolada executada.", flush=True)
        # A suíte de navegador e o browser.lock são gates separados, ainda pendentes.
        report["status"] = "PARCIAL"
        return 0
    except (ValidationError, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as exc:
        if report["results"][stage] == "NAO_EXECUTADO":
            report["results"][stage] = "FALHOU"
        report["status"] = "BLOQUEADO"
        report["error"] = str(exc)
        print(f"[BLOQUEADO] {exc}", file=sys.stderr, flush=True)
        return 1
    finally:
        if qa_started:
            try:
                compose(qa_name, AUDIT, env=env,
                        args=["cp", "tests:/app/test-results/.", str(output)], quiet=True)
            except (ValidationError, OSError):
                print("[AVISO] Evidências da suíte indisponíveis.", file=sys.stderr)
            try:
                compose(qa_name, AUDIT, env=env, args=["down"], quiet=True)
            except (ValidationError, OSError):
                print("[AVISO] Examine a stack QA isolada; não houve remoção de volumes.", file=sys.stderr)
        if started:
            try:
                compose(name, VALIDATION, env=env, args=["down"], quiet=True)
            except (ValidationError, OSError):
                print("[AVISO] Examine a stack de validação isolada.", file=sys.stderr)
        report["finished"] = datetime.now().isoformat(timespec="seconds")
        logs = Path.home() / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        log_path = logs / f"{stamp}__{name}.log"
        report["log"] = str(log_path)
        summary = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        log_path.write_text(summary, encoding="utf-8")
        (output / "resultado.json").write_text(summary, encoding="utf-8")
        print("Resultados:", output, flush=True)
        if started:
            print("Volumes de validação preservados para inspeção; nenhum -v foi executado.", flush=True)
        else:
            print("Nenhum recurso Docker foi inicializado.", flush=True)


if __name__ == "__main__":
    sys.exit(main())
