# SPDX-License-Identifier: GPL-3.0-only
from django.urls import path, register_converter
from apps.finance.route_converters import KindConverter, ReportConverter
register_converter(KindConverter, "tipo")
register_converter(ReportConverter, "relatorio")

from apps.finance import views
from apps.finance import grant_views, transaction_views, import_views, categorization_views, reports_views, financial_transfer_views

app_name = "finance"
urlpatterns = [
    path("nucleos/<int:workspace_id>/perfis/", views.profile_list, name="profile-list"),
    path("nucleos/<int:workspace_id>/perfis/novo/", views.profile_create, name="profile-create"),
    path("perfis/<int:profile_id>/", views.profile_detail, name="profile-detail"),
    path("perfis/<int:profile_id>/contas/novo/", views.account_create, name="account-create"),
    path("nucleos/<int:workspace_id>/escolher-perfil/<str:operation>/", views.choose_profile_for_action, name="choose-profile-action"),
    path("nucleos/<int:workspace_id>/", views.workspace_page, name="overview"),
    path("nucleos/<int:workspace_id>/despesas/", views.workspace_page,
         {"section": "expenses"}, name="expenses"),
    path("nucleos/<int:workspace_id>/investimentos/", views.workspace_page,
         {"section": "investments"}, name="investments"),
    path("nucleos/<int:workspace_id>/movimentacoes/", views.workspace_page,
         {"section": "movements"}, name="movements"),
    path("perfis/<int:profile_id>/gerenciar/", views.profile_manage, name="profile-manage"),
    path("perfis/<int:profile_id>/editar/", views.profile_edit, name="profile-edit"),
    path("perfis/<int:profile_id>/renda/", views.income_edit, name="income-edit"),
    path("nucleos/<int:workspace_id>/rendas/", views.income_bulk_edit, name="income-bulk"),
    path("perfis/<int:profile_id>/reserva/", views.record_edit, {"kind": "reserve"}, name="reserve-edit"),
    path("perfis/<int:profile_id>/permissoes/", grant_views.grant_list, name="grant-list"),
    path("perfis/<int:profile_id>/permissoes/<int:membership_id>/", grant_views.grant_edit, name="grant-edit"),
    path("perfis/<int:profile_id>/pagar/<tipo:kind>/<int:object_id>/", transaction_views.payment, name="payment"),
    path("perfis/<int:profile_id>/desmarcar/<tipo:kind>/<int:object_id>/", transaction_views.reverse_item, name="reverse-item"),
    path("perfis/<int:profile_id>/transferir/", transaction_views.transfer_view, name="transfer"),
    path("perfis/<int:profile_id>/investimentos/<int:investment_id>/resgatar/", transaction_views.withdrawal, name="withdrawal"),
    path("perfis/<int:profile_id>/movimentacoes/<int:batch_id>/", transaction_views.movement_detail, name="movement-detail"),
    path("perfis/<int:profile_id>/movimentacoes/<int:batch_id>/estornar/", transaction_views.reverse_movement, name="reverse-movement"),
    
    # Importação bancária
    path("nucleos/<int:workspace_id>/importacoes/", import_views.import_list, name="import-list"),
    path("perfis/<int:profile_id>/importacoes/novo/", import_views.import_upload, name="import-upload"),
    path("perfis/<int:profile_id>/importacoes/<int:batch_id>/", import_views.import_preview, name="import-preview"),
    path("perfis/<int:profile_id>/importacoes/<int:batch_id>/simulacao/", import_views.import_dry_run, name="import-dry-run"),
    path("perfis/<int:profile_id>/importacoes/<int:batch_id>/confirmar/", import_views.import_commit, name="import-commit"),
    path("perfis/<int:profile_id>/importacoes/<int:batch_id>/relatorio/", import_views.import_report, name="import-report"),
    path("perfis/<int:profile_id>/importacoes/<int:batch_id>/linhas/<int:row_id>/editar/", import_views.import_row_edit, name="import-row-edit"),
    path("perfis/<int:profile_id>/importacoes/<int:batch_id>/linhas/<int:row_id>/", import_views.import_row_detail, name="import-row-detail"),
    
    # Regras de Categorização (De-Para)
    path("nucleos/<int:workspace_id>/categorizacao/", categorization_views.categorization_list, name="categorization-list"),
    path("nucleos/<int:workspace_id>/categorizacao/novo/", categorization_views.categorization_create, name="categorization-create"),
    path("nucleos/<int:workspace_id>/categorizacao/<int:rule_id>/editar/", categorization_views.categorization_edit, name="categorization-edit"),
    path("nucleos/<int:workspace_id>/categorizacao/<int:rule_id>/excluir/", categorization_views.categorization_delete, name="categorization-delete"),
    path("nucleos/<int:workspace_id>/categorizacao/testar/", categorization_views.categorization_test, name="categorization-test"),
    
    # Transferência financeira técnica (sem usuários, permissões, logs ou secrets).
    path("nucleos/<int:workspace_id>/relatorios/tecnico/", financial_transfer_views.technical_reports, name="technical-reports"),
    path("nucleos/<int:workspace_id>/relatorios/tecnico/exportar/", financial_transfer_views.export_financial, name="financial-export"),
    path("nucleos/<int:workspace_id>/relatorios/tecnico/importar/", financial_transfer_views.import_financial, name="financial-import"),

    # Relatórios Financeiros (Sprint 05)
    path("nucleos/<int:workspace_id>/relatorios/", reports_views.reports_dashboard, name="reports-dashboard"),
    path("nucleos/<int:workspace_id>/perfis/<int:profile_id>/relatorios/dre/", reports_views.dre_report, name="dre-report"),
    path("nucleos/<int:workspace_id>/perfis/<int:profile_id>/relatorios/patrimonio/", reports_views.equity_evolution_report, name="equity-report"),
    path("nucleos/<int:workspace_id>/perfis/<int:profile_id>/relatorios/investimentos/", reports_views.investment_report, name="investment-report"),
    path("nucleos/<int:workspace_id>/perfis/<int:profile_id>/relatorios/metas/", reports_views.goals_report, name="goals-report"),
    path("nucleos/<int:workspace_id>/perfis/<int:profile_id>/relatorios/exportar/<relatorio:report_type>/", reports_views.export_report, name="export-report"),
]

ROUTE_KIND = {"account": "conta", "recurring": "recorrentes", "unexpected": "imprevistas", "investment": "investimento"}
for kind in ("account", "recurring", "unexpected", "investment"):
    slug = ROUTE_KIND[kind]
    if kind != "account":
        urlpatterns.append(path(f"perfis/<int:profile_id>/{slug}/novo/", views.record_edit,
            {"kind": kind}, name=f"{kind}-create",
        ))
    urlpatterns.extend([
        path(f"perfis/<int:profile_id>/{slug}/<int:object_id>/editar/", views.record_edit,
             {"kind": kind}, name=f"{kind}-edit"),
        path(f"perfis/<int:profile_id>/{slug}/<int:object_id>/excluir/", views.record_delete,
             {"kind": kind}, name=f"{kind}-delete"),
    ])
