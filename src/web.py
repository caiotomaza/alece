# Gerenciamento central das rotas WEB (Django URLconf).
# SPDX-License-Identifier: GPL-3.0-only
from django.contrib import admin
from django.urls import include, path

from apps.core import views
from apps.core import auth_views
from apps.core import user_views, settings_views
from apps.core.auth_forms import ThrottledAdminAuthenticationForm
from apps.finance import public_routes
from apps.core.preferences import set_theme_preference

admin.site.login_form = ThrottledAdminAuthenticationForm

class WebRoutes:
    """Registry of ALECE HTTP routes; legacy app URLconfs are included unchanged.

    Centralization of public URLs follows the familiar Laravel web routes pattern,
    while preserving Django route names and the reverse() API.
    """

    @staticmethod
    def build():
        return [
            # Rotas historicas preservadas, sem alterar verbos POST ou descarte de corpos.
            path("finance/", include("apps.finance.legacy_urls")),
            path("core/", include("apps.core.legacy_urls")),
            path("health/live/", views.live),
            path("health/ready/", views.ready),
            path("healthz/", views.healthz),
            path("about/", views.about_page),
            path("setup/", user_views.setup_view),
            path("login/", auth_views.login_view),
            path("logout/", auth_views.logout_view),
            path("password/change/", auth_views.password_change_view),
            path("recovery/", auth_views.recovery_code_request_view),
            path("recovery/use/", auth_views.recovery_code_use_view),
            path("recovery/generate/", auth_views.recovery_code_generate_view),
            path("admin/", admin.site.urls),

            path("", views.index, name="home"),
            path("visao-geral/", public_routes.public_page, {"section": "overview"}, name="visao-geral"),
            path("despesas/", public_routes.public_page, {"section": "expenses"}, name="despesas"),
            path("investimentos/", public_routes.public_page, {"section": "investments"}, name="investimentos"),
            path("movimentacoes/", public_routes.public_page, {"section": "movements"}, name="movimentacoes"),
            path("configuracoes/", public_routes.public_page, {"section": "settings"}, name="configuracoes"),
            path("configuracoes/usuarios/", settings_views.settings_admin_panel, {"panel": "usuarios"}, name="configuracoes-usuarios"),
            path("configuracoes/perfis/", settings_views.settings_admin_panel, {"panel": "perfis"}, name="configuracoes-perfis"),
            path("configuracoes/apis/", settings_views.settings_admin_panel, {"panel": "apis"}, name="configuracoes-apis"),
            path("logs/", views.system_logs_list, name="logs"),
            path("logs/diagnostico/", views.system_logs_diagnostic, name="logs-diagnostico"),
            path("relatorios/", public_routes.public_technical_reports, name="relatorios"),
            path("relatorios/exportar/", public_routes.public_financial_export, name="relatorios-exportar"),
            path("relatorios/importar/", public_routes.public_financial_import, name="relatorios-importar"),
            path("configuracoes/minha-conta/", settings_views.my_information, name="configuracoes-minha-conta"),
            path("configuracoes/codigos/", settings_views.recovery_status, name="configuracoes-codigos"),
            path("configuracoes/api/nova/", settings_views.provider_form, name="configuracoes-api-nova"),
            path("configuracoes/api/<int:provider_id>/editar/", settings_views.provider_form, name="configuracoes-api-editar"),
            path("configuracoes/api/<int:provider_id>/excluir/", settings_views.provider_delete, name="configuracoes-api-excluir"),
            path("configuracoes/api/<int:provider_id>/selecionar/", settings_views.provider_select, name="configuracoes-api-selecionar"),
            path("configuracoes/api/<int:provider_id>/analisar/", settings_views.analyze_imports, name="configuracoes-api-analisar"),
            path("selecionar-nucleo/<int:workspace_id>/", public_routes.select_workspace, name="selecionar-nucleo"),
            path("preferencias/tema/", set_theme_preference, name="preferencia-tema"),
            path("financas/", include("apps.finance.urls")),
            path("sistema/", include("apps.core.urls")),
            path("saude/ativo/", views.live, name="health-live"),
            path("saude/pronto/", views.ready, name="health-ready"),
            path("saude/", views.healthz, name="healthz"),
            path("sobre/", views.about_page, name="about-page"),
            # Configuração inicial (bootstrap)
            path("configuracao-inicial/", user_views.setup_view, name="setup"),
            # Autenticação
            path("entrar/", auth_views.login_view, name="login"),
            path("sair/", auth_views.logout_view, name="logout"),
            path("senha/alterar/", auth_views.password_change_view, name="password_change"),
            # Recuperação offline
            path("recuperacao/", auth_views.recovery_code_request_view, name="recovery_request"),
            path("recuperacao/usar/", auth_views.recovery_code_use_view, name="recovery_use"),
            path("recuperacao/gerar/", auth_views.recovery_code_generate_view, name="recovery_generate"),
            # Admin
            path("administracao/", admin.site.urls),
        ]


urlpatterns = WebRoutes.build()

# Handlers fora dos includes, conforme a documentacao Django.
handler400 = "apps.core.error_views.error400"
handler403 = "apps.core.error_views.error403"
handler404 = "apps.core.error_views.error404"
handler500 = "apps.core.error_views.error500"
