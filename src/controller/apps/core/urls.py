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
    user_delete_account,
    setup_view,
)

app_name = "core"
urlpatterns = [
    # Configuração inicial (bootstrap)
    path("configuracao-inicial/", setup_view, name="setup"),
    # Logs do Sistema
    path("logs-sistema/", views.system_logs_legacy_redirect, name="system-logs-list"),
    path("logs-sistema/<int:log_id>/", views.system_log_detail, name="system-log-detail"),
    # Gestão de usuários (apenas Admin)
    path("usuarios/<int:workspace_id>/", user_management, name="user-management"),
    path("usuarios/<int:workspace_id>/<int:user_id>/editar/", user_edit, name="user-edit"),
    path("usuarios/<int:workspace_id>/<int:user_id>/remover/", user_remove_access, name="user-remove-access"),
    path("usuarios/<int:workspace_id>/<int:user_id>/excluir/", user_delete_account, name="user-delete-account"),
    path("usuarios/<int:workspace_id>/<int:user_id>/senha/", user_password_reset, name="user-password-reset"),
    path("usuarios/<int:workspace_id>/<int:user_id>/revogar-sessoes/", user_revoke_sessions, name="user-revoke-sessions"),
    path("permissoes/<int:workspace_id>/<int:membership_id>/", grant_management, name="grant-management"),
]