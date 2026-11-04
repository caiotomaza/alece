# SPDX-License-Identifier: GPL-3.0-only
"""Django settings for tests; static assets are served without a collected manifest."""
from config.settings import *  # noqa: F403

ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
# Existing view suites seed users without enrollment; dedicated recovery tests enable this.
ALECE_REQUIRE_RECOVERY_SETUP = False
