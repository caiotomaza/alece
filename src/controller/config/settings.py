# SPDX-License-Identifier: GPL-3.0-only
"""Configuração por variáveis de ambiente; sem valores secretos versionados."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]

# Carregar .env antes de acessar variáveis de ambiente
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


def environment_secret(name: str) -> str:
    """Read from env, or a volume-backed secret file (Docker)."""
    value = os.environ.get(name, "")
    if value:
        return value
    filename = os.environ.get(f"{name}_FILE", "")
    if filename:
        return Path(filename).read_text(encoding="utf-8").strip()
    return ""


SECRET_KEY = environment_secret("ALECE_SECRET_KEY")
if not SECRET_KEY or SECRET_KEY.startswith("CHANGE_ME"):
    raise RuntimeError("ALECE_SECRET_KEY ausente. Use um segredo aleatório em .env.")

DEBUG = env_bool("ALECE_DEBUG")
ALECE_BIND_IP = os.environ.get("ALECE_BIND_IP", "127.0.0.1").strip()

# Configuração de proxy reverso opcional
USE_X_FORWARDED_HOST = env_bool("ALECE_USE_X_FORWARDED_HOST", False)
USE_X_FORWARDED_PORT = env_bool("ALECE_USE_X_FORWARDED_PORT", False)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if env_bool("ALECE_SECURE_PROXY_SSL", False) else None

ALLOWED_HOSTS = env_list("ALECE_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
CSRF_TRUSTED_ORIGINS = env_list("ALECE_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core",
    "apps.finance",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.SystemInitializationMiddleware",
    "apps.core.middleware.RecoveryEnrollmentMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "src" / "view" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.privacy_mode",
                "apps.core.context_processors.ui_theme",
            ],
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("ALECE_DB_NAME", "alece"),
        "USER": os.environ.get("ALECE_DB_USER", "alece"),
        "PASSWORD": environment_secret("ALECE_DB_PASSWORD"),
        "HOST": os.environ.get("ALECE_DB_HOST", "db"),
        "PORT": os.environ.get("ALECE_DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Fortaleza"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "src" / "view" / "static"]
STATIC_ROOT = BASE_DIR / ".staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = env_bool("ALECE_SECURE_COOKIES", False)
CSRF_COOKIE_SECURE = env_bool("ALECE_SECURE_COOKIES", False)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"
# O capturador do container mantém stdout/stderr no Docker e, quando ativado,
# duplica a saída para um arquivo distinto por inicialização em src/logs/.
# A configuração do Django não abre o mesmo arquivo nos múltiplos workers.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detalhado": {
            "format": "%(asctime)s %(levelname)s [pid=%(process)d] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {"console": {
        "class": "logging.StreamHandler",
        "formatter": "detalhado",
    }},
    "root": {"handlers": ["console"], "level": os.getenv("ALECE_LOG_LEVEL", "INFO")},
}

# Mandatory six-code enrollment on all production installations.
ALECE_REQUIRE_RECOVERY_SETUP = True
