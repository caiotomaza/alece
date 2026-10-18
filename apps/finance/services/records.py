# SPDX-License-Identifier: GPL-3.0-only
"""Authorized, transactional registration operations; registrations never move cash."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.core.permissions import require_profile_edit, require_workspace_admin
from apps.finance.models import (
    BankAccount, FinancialProfile, InvestmentPosition, RecurringExpense, ReservePolicy,
    UnexpectedExpense,
)

FIELDS = {
    BankAccount: {"name", "kind", "balance", "is_archived"},
    RecurringExpense: {"name", "category", "amount", "due_day", "is_active"},
    UnexpectedExpense: {"name", "amount"},
    InvestmentPosition: {"name", "institution", "category", "applied_amount", "current_value", "target_amount", "is_active", "recorded_on"},
    ReservePolicy: {"coverage_months"},
}


def locked_profile(user, profile_id):
    require_profile_edit(user, profile_id)
    profile = FinancialProfile.objects.select_for_update().get(pk=profile_id)
    if profile.is_archived:
        raise ValidationError("Reative o perfil antes de alterar seus cadastros.")
    return profile


def has_history(obj):
    if isinstance(obj, BankAccount):
        return obj.ledgerleg_set.exists()
    if isinstance(obj, (RecurringExpense, UnexpectedExpense, InvestmentPosition)):
        return obj.transactionbatch_set.exists()
    return False


@transaction.atomic
def save_record(user, profile_id, model, data, object_id=None):
    if model not in FIELDS or set(data) - FIELDS[model]:
        raise ValidationError("Cadastro ou campo não permitido.")
    profile = locked_profile(user, profile_id)
    if model is ReservePolicy:
        require_workspace_admin(user, profile.workspace_id)
    if object_id is not None:
        obj = model.objects.select_for_update().get(pk=object_id, profile=profile)
    elif model is ReservePolicy:
        obj = model.objects.select_for_update().filter(profile=profile).first() or model(profile=profile)
    else:
        obj = model(profile=profile)
    if obj.pk and has_history(obj):
        # Names and visibility can change; cash, position and historical classifications cannot.
        safe_fields = {"name", "institution", "is_active", "is_archived", "target_amount"}
        if isinstance(obj, RecurringExpense):
            safe_fields |= {"amount", "due_day"}  # changes apply to future monthly planning
        if isinstance(obj, UnexpectedExpense):
            safe_fields = set()
        changed = {key for key, value in data.items() if getattr(obj, key) != value}
        if changed - safe_fields:
            raise ValidationError("Registro com movimentações: alteração financeira exige conciliação.")
    for key, value in data.items():
        setattr(obj, key, value.strip() if isinstance(value, str) else value)
    if model is UnexpectedExpense and not obj.pk:
        obj.recorded_on = timezone.localdate()
    obj.full_clean()
    obj.save()
    return obj


@transaction.atomic
def delete_record(user, profile_id, model, object_id):
    if model not in FIELDS or model is ReservePolicy:
        raise ValidationError("Exclusão não permitida.")
    profile = locked_profile(user, profile_id)
    obj = model.objects.select_for_update().get(pk=object_id, profile=profile)
    if has_history(obj):
        raise ValidationError("O histórico deve ser preservado. Arquive o cadastro quando disponível.")
    obj.delete()


@transaction.atomic
def update_income(user, profile_id, monthly_income):
    profile = locked_profile(user, profile_id)
    profile.monthly_income = monthly_income
    profile.full_clean()
    profile.save(update_fields=["monthly_income"])
    return profile
