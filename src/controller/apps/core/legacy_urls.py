# SPDX-License-Identifier: GPL-3.0-only
from django.urls import path

from apps.core import views
from apps.core.user_views import (
    grant_management,
    user_edit,
    user_management,
    user_password_reset,
    user_revoke_sessions,
    user_remove_access,
    setup_view,
)

app_name = "sistema_anterior"
urlpatterns = [
    # Configuração inicial (bootstrap)
    path("setup/", setup_view, name="setup"),
    # Logs do Sistema
    path("system-logs/", views.system_logs_legacy_redirect, name="system-logs-list"),
    path("system-logs/<int:log_id>/", views.system_log_detail, name="system-log-detail"),
    # Gestão de usuários (apenas Admin)
    path("users/<int:workspace_id>/", user_management, name="user-management"),
    path("users/<int:workspace_id>/<int:user_id>/edit/", user_edit, name="user-edit"),
    path("users/<int:workspace_id>/<int:user_id>/remove/", user_remove_access, name="user-remove-access"),
    path("users/<int:workspace_id>/<int:user_id>/password/", user_password_reset, name="user-password-reset"),
    path("core/users/<int:workspace_id>/<int:user_id>/revoke-sessions/", user_revoke_sessions, name="user-revoke-sessions"),
    path("grants/<int:workspace_id>/<int:membership_id>/", grant_management, name="grant-management"),
]