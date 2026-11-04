# SPDX-License-Identifier: GPL-3.0-only
"""Django entrypoint: canonical routing rules reside in src/web.py."""
from src.web import urlpatterns, handler400, handler403, handler404, handler500
