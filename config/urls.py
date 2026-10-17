# SPDX-License-Identifier: GPL-3.0-only
from django.contrib import admin
from django.urls import path

from apps.core import views
from apps.core import auth_views

urlpatterns = [
    path("", views.index, name="home"),
    path("health/live/", views.live, name="health-live"),
    path("health/ready/", views.ready, name="health-ready"),
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