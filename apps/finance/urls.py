# SPDX-License-Identifier: GPL-3.0-only
from django.urls import path

from apps.finance import views
from apps.finance import grant_views, transaction_views, import_views, categorization_views, reports_views

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
    path("workspaces/<int:workspace_id>/movements/", views.workspace_page,
         {"section": "movements"}, name="movements"),
    path("profiles/<int:profile_id>/edit/", views.profile_edit, name="profile-edit"),
    path("profiles/<int:profile_id>/income/", views.income_edit, name="income-edit"),
    path("profiles/<int:profile_id>/reserve/", views.record_edit, {"kind": "reserve"}, name="reserve-edit"),
    path("profiles/<int:profile_id>/grants/", grant_views.grant_list, name="grant-list"),
    path("profiles/<int:profile_id>/grants/<int:membership_id>/", grant_views.grant_edit, name="grant-edit"),
    path("profiles/<int:profile_id>/pay/<str:kind>/<int:object_id>/", transaction_views.payment, name="payment"),
    path("profiles/<int:profile_id>/uncheck/<str:kind>/<int:object_id>/", transaction_views.reverse_item, name="reverse-item"),
    path("profiles/<int:profile_id>/transfer/", transaction_views.transfer_view, name="transfer"),
    path("profiles/<int:profile_id>/investments/<int:investment_id>/withdraw/", transaction_views.withdrawal, name="withdrawal"),
    path("profiles/<int:profile_id>/movements/<int:batch_id>/", transaction_views.movement_detail, name="movement-detail"),
    path("profiles/<int:profile_id>/movements/<int:batch_id>/reverse/", transaction_views.reverse_movement, name="reverse-movement"),
    
    # Importação bancária
    path("workspaces/<int:workspace_id>/imports/", import_views.import_list, name="import-list"),
    path("profiles/<int:profile_id>/imports/new/", import_views.import_upload, name="import-upload"),
    path("profiles/<int:profile_id>/imports/<int:batch_id>/", import_views.import_preview, name="import-preview"),
    path("profiles/<int:profile_id>/imports/<int:batch_id>/dry-run/", import_views.import_dry_run, name="import-dry-run"),
    path("profiles/<int:profile_id>/imports/<int:batch_id>/commit/", import_views.import_commit, name="import-commit"),
    path("profiles/<int:profile_id>/imports/<int:batch_id>/report/", import_views.import_report, name="import-report"),
    path("profiles/<int:profile_id>/imports/<int:batch_id>/rows/<int:row_id>/edit/", import_views.import_row_edit, name="import-row-edit"),
    path("profiles/<int:profile_id>/imports/<int:batch_id>/rows/<int:row_id>/", import_views.import_row_detail, name="import-row-detail"),
    
    # Regras de Categorização (De-Para)
    path("workspaces/<int:workspace_id>/categorization/", categorization_views.categorization_list, name="categorization-list"),
    path("workspaces/<int:workspace_id>/categorization/new/", categorization_views.categorization_create, name="categorization-create"),
    path("workspaces/<int:workspace_id>/categorization/<int:rule_id>/edit/", categorization_views.categorization_edit, name="categorization-edit"),
    path("workspaces/<int:workspace_id>/categorization/<int:rule_id>/delete/", categorization_views.categorization_delete, name="categorization-delete"),
    path("workspaces/<int:workspace_id>/categorization/test/", categorization_views.categorization_test, name="categorization-test"),
    
    # Relatórios Financeiros (Sprint 05)
    path("workspaces/<int:workspace_id>/reports/", reports_views.reports_dashboard, name="reports-dashboard"),
    path("profiles/<int:profile_id>/reports/dre/", reports_views.dre_report, name="dre-report"),
    path("profiles/<int:profile_id>/reports/equity/", reports_views.equity_evolution_report, name="equity-report"),
    path("profiles/<int:profile_id>/reports/investments/", reports_views.investment_report, name="investment-report"),
    path("profiles/<int:profile_id>/reports/goals/", reports_views.goals_report, name="goals-report"),
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
