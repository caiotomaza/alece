# SPDX-License-Identifier: GPL-3.0-only
from django.urls import path

from apps.finance import views

app_name = "finance"
urlpatterns = [
    path("workspaces/<int:workspace_id>/profiles/", views.profile_list, name="profile-list"),
    path("workspaces/<int:workspace_id>/profiles/new/", views.profile_create, name="profile-create"),
    path("profiles/<int:profile_id>/", views.profile_detail, name="profile-detail"),
    path("profiles/<int:profile_id>/accounts/new/", views.account_create, name="account-create"),
    path("workspaces/<int:workspace_id>/", views.workspace_page, name="overview"),
    path("workspaces/<int:workspace_id>/expenses/", views.workspace_page,
         {"section": "expenses"}, name="expenses"),
    path("workspaces/<int:workspace_id>/investments/", views.workspace_page,
         {"section": "investments"}, name="investments"),
    path("profiles/<int:profile_id>/edit/", views.profile_edit, name="profile-edit"),
    path("profiles/<int:profile_id>/income/", views.income_edit, name="income-edit"),
    path("profiles/<int:profile_id>/reserve/", views.record_edit, {"kind": "reserve"}, name="reserve-edit"),
]

for kind in ("account", "recurring", "unexpected", "investment"):
    if kind != "account":
        urlpatterns.append(path(
            f"profiles/<int:profile_id>/{kind}/new/", views.record_edit,
            {"kind": kind}, name=f"{kind}-create",
        ))
    urlpatterns.extend([
        path(f"profiles/<int:profile_id>/{kind}/<int:object_id>/edit/", views.record_edit,
             {"kind": kind}, name=f"{kind}-edit"),
        path(f"profiles/<int:profile_id>/{kind}/<int:object_id>/delete/", views.record_delete,
             {"kind": kind}, name=f"{kind}-delete"),
    ])
