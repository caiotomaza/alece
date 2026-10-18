# SPDX-License-Identifier: GPL-3.0-only
"""Django settings for tests; static assets are served without a collected manifest."""
from config.settings import *  # noqa: F403

STORAGES = {
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
