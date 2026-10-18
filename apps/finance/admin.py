# SPDX-License-Identifier: GPL-3.0-only
from django.contrib import admin

from .models import (
    BankAccount,
    FinancialProfile,
    InvestmentPosition,
    JournalEntry,
    LedgerLeg,
    MonthlyExpense,
    MonthlyInvestmentPlan,
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


class FinancialReadOnlyAdmin(SuperuserOnlyAdmin):
    """Cadastros financeiros são alterados apenas pelos serviços do produto."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


for model in (Workspace, WorkspaceMembership, ProfileGrant):
    admin.site.register(model, SuperuserOnlyAdmin)

for model in (
    FinancialProfile,
    BankAccount, RecurringExpense, UnexpectedExpense, InvestmentPosition,
    ReservePolicy, TransactionBatch, LedgerLeg, JournalEntry, MonthlyExpense,
    MonthlyInvestmentPlan,
):
    admin.site.register(model, FinancialReadOnlyAdmin)
