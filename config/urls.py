# SPDX-License-Identifier: GPL-3.0-only
from django.contrib import admin
from django.urls import include, path

from apps.core import views
from apps.core import auth_views
from apps.core.auth_forms import ThrottledAdminAuthenticationForm

admin.site.login_form = ThrottledAdminAuthenticationForm

urlpatterns = [
    path("", views.index, name="home"),
    path("finance/", include("apps.finance.urls")),
    path("health/live/", views.live, name="health-live"),
    path("health/ready/", views.ready, name="health-ready"),
    path("healthz/", views.healthz, name="healthz"),
    path("about/", views.about_page, name="about-page"),
    # Autenticação
    path("login/", auth_views.login_view, name="login"),
    path("logout/", auth_views.logout_view, name="logout"),
    path("password/change/", auth_views.password_change_view, name="password_change"),
    # Recuperação offline
    path("recovery/", auth_views.recovery_code_request_view, name="recovery_request"),
    path("recovery/use/", auth_views.recovery_code_use_view, name="recovery_use"),
    path("recovery/generate/", auth_views.recovery_code_generate_view, name="recovery_generate"),
    # Admin
    path("admin/", admin.site.urls),
]
