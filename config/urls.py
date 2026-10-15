# SPDX-License-Identifier: GPL-3.0-only
from django.contrib import admin
from django.urls import path

from apps.core import views

urlpatterns = [
    path("", views.index, name="home"),
    path("health/live/", views.live, name="health-live"),
    path("health/ready/", views.ready, name="health-ready"),
    path("admin/", admin.site.urls),
]
