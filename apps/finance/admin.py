# SPDX-License-Identifier: GPL-3.0-only
from django.contrib import admin

from .models import (
    BankAccount,
    FinancialProfile,
    InvestmentPosition,
    LedgerLeg,
    ProfileGrant,
    RecurringExpense,
    ReservePolicy,
    TransactionBatch,
    UnexpectedExpense,
    Workspace,
    WorkspaceMembership,
)


class SuperuserOnlyAdmin(admin.ModelAdmin):
    """ACL final será aplicada nas views/services. Django Admin é ferramenta de operador."""

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser


for model in (
    Workspace, WorkspaceMembership, FinancialProfile, ProfileGrant,
    BankAccount, RecurringExpense, UnexpectedExpense, InvestmentPosition,
    ReservePolicy, TransactionBatch, LedgerLeg,
):
    admin.site.register(model, SuperuserOnlyAdmin)
