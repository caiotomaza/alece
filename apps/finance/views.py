# SPDX-License-Identifier: GPL-3.0-only
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.core.permissions import (
    get_accessible_profiles, require_profile_edit, require_profile_view,
    require_workspace_access, require_workspace_admin, user_can_edit_profile,
    user_is_workspace_admin,
)
from apps.finance.forms import BankAccountForm, FinancialProfileForm
from apps.finance.models import (
    BankAccount, InvestmentPosition, RecurringExpense,
    ReservePolicy, UnexpectedExpense, Workspace,
)
from apps.finance.query_forms import IncomeForm, WorkspaceFilterForm
from apps.finance.services.metrics import profile_summary
from apps.finance.services.records import delete_record, save_record, update_income
from apps.finance.services.profiles import update_financial_profile
from apps.finance.services.profiles import create_financial_profile


def add_validation_errors(form, error):
    if hasattr(error, "error_dict"):
        for field, errors in error.error_dict.items():
            form.add_error(field if field in form.fields else None, errors)
    else:
        form.add_error(None, error)


@login_required
@require_http_methods(["GET"])
def profile_list(request, workspace_id):
    require_workspace_access(request.user, workspace_id)
    workspace = get_object_or_404(Workspace, pk=workspace_id)
    return render(request, "finance/profile_list.html", {
        "workspace": workspace,
        "profiles": get_accessible_profiles(request.user).filter(workspace=workspace).order_by("is_archived", "pk"),
        "active_nav": "profiles",
        "can_create": user_is_workspace_admin(request.user, workspace_id),
    })


@login_required
@require_http_methods(["GET", "POST"])
def profile_create(request, workspace_id):
    require_workspace_admin(request.user, workspace_id)
    workspace = get_object_or_404(Workspace, pk=workspace_id)
    form = FinancialProfileForm(request.POST if request.method == "POST" else None)
    form.fields.pop("is_archived", None)
    if request.method == "POST" and form.is_valid():
        try:
            profile = create_financial_profile(
                workspace_id=workspace.pk, created_by=request.user, **form.cleaned_data,
            )
        except ValidationError as error:
            add_validation_errors(form, error)
        else:
            messages.success(request, "Perfil financeiro criado.")
            return redirect("finance:profile-detail", profile_id=profile.pk)
    return render(request, "finance/object_form.html", {
        "workspace": workspace, "form": form, "title": "Novo perfil financeiro",
        "cancel_url": reverse("finance:profile-list", args=[workspace.pk]),
    })


@login_required
@require_http_methods(["GET"])
def profile_detail(request, profile_id):
    profile = require_profile_view(request.user, profile_id)
    return render(request, "finance/profile_detail.html", {
        "profile": profile, "accounts": profile.accounts.order_by("pk"),
        "workspace": profile.workspace,
        "can_admin": user_is_workspace_admin(request.user, profile.workspace_id),
        "can_edit": user_can_edit_profile(request.user, profile_id) and not profile.is_archived,
    })


@login_required
@require_http_methods(["GET", "POST"])
def account_create(request, profile_id):
    profile = editable_profile(request.user, profile_id)
    form = BankAccountForm(request.POST if request.method == "POST" else None)
    form.fields.pop("is_archived", None)
    if request.method == "POST" and form.is_valid():
        try:
            save_record(request.user, profile.pk, BankAccount, form.cleaned_data)
        except ValidationError as error:
            add_validation_errors(form, error)
        else:
            messages.success(request, "Conta criada.")
            return redirect("finance:profile-detail", profile_id=profile.pk)
    return render(request, "finance/object_form.html", {
        "profile": profile, "workspace": profile.workspace, "form": form, "title": "Nova conta",
        "cancel_url": reverse("finance:profile-detail", args=[profile.pk]),
    })


@login_required
@require_http_methods(["GET", "POST"])
def profile_edit(request, profile_id):
    profile = require_profile_view(request.user, profile_id)
    require_workspace_admin(request.user, profile.workspace_id)
    form = FinancialProfileForm(request.POST if request.method == "POST" else None, instance=profile)
    if request.method == "POST" and form.is_valid():
        try:
            update_financial_profile(request.user, profile.pk, form.cleaned_data)
        except ValidationError as error:
            add_validation_errors(form, error)
        else:
            messages.success(request, "Perfil atualizado.")
            return redirect("finance:profile-detail", profile_id=profile.pk)
    return render(request, "finance/object_form.html", {
        "form": form, "title": "Editar perfil financeiro", "object": profile,
        "workspace": profile.workspace, "profile": profile,
        "cancel_url": reverse("finance:profile-detail", args=[profile.pk]),
    })


def editable_profile(user, profile_id):
    profile = require_profile_view(user, profile_id)
    require_profile_edit(user, profile_id)
    if profile.is_archived:
        raise PermissionDenied("Perfil arquivado: reative antes de alterar seus cadastros.")
    return profile


@login_required
@require_http_methods(["GET", "POST"])
def income_edit(request, profile_id):
    profile = editable_profile(request.user, profile_id)
    form = IncomeForm(request.POST if request.method == "POST" else None,
                      initial={"monthly_income": profile.monthly_income})
    if request.method == "POST" and form.is_valid():
        try:
            update_income(request.user, profile.pk, form.cleaned_data["monthly_income"])
        except ValidationError as error:
            add_validation_errors(form, error)
        else:
            messages.success(request, "Renda atualizada. Nenhuma movimentação bancária foi realizada.")
            return redirect("finance:profile-detail", profile_id=profile.pk)
    return render(request, "finance/object_form.html", {
        "form": form, "title": "Editar renda mensal", "workspace": profile.workspace,
        "cancel_url": reverse("finance:profile-detail", args=[profile.pk]),
    })


def record_config(kind):
    from apps.finance.forms import (
        InvestmentPositionForm, RecurringExpenseForm, ReservePolicyForm, UnexpectedExpenseForm,
    )
    return {
        "account": (BankAccount, BankAccountForm, "conta", "profile-detail"),
        "recurring": (RecurringExpense, RecurringExpenseForm, "despesa previsível", "expenses"),
        "unexpected": (UnexpectedExpense, UnexpectedExpenseForm, "despesa imprevisível", "expenses"),
        "investment": (InvestmentPosition, InvestmentPositionForm, "posição de investimento", "investments"),
        "reserve": (ReservePolicy, ReservePolicyForm, "cobertura da Reserva", "investments"),
    }[kind]


def record_return_url(profile, route):
    return reverse(f"finance:{route}", args=[profile.pk if route == "profile-detail" else profile.workspace_id])


@login_required
@require_http_methods(["GET", "POST"])
def record_edit(request, profile_id, kind, object_id=None):
    profile = editable_profile(request.user, profile_id)
    model, form_class, label, route = record_config(kind)
    if kind == "reserve":
        require_workspace_admin(request.user, profile.workspace_id)
        instance = model.objects.filter(profile=profile).first()
        object_id = instance.pk if instance else None
    else:
        instance = get_object_or_404(model, pk=object_id, profile=profile) if object_id else None
    form = form_class(request.POST if request.method == "POST" else None, instance=instance)
    if not instance:
        for field in ("is_archived", "is_active"):
            form.fields.pop(field, None)
    if request.method == "POST" and form.is_valid():
        try:
            save_record(request.user, profile.pk, model, form.cleaned_data, object_id=object_id)
        except ValidationError as error:
            add_validation_errors(form, error)
        else:
            messages.success(request, "Cadastro salvo. Nenhuma movimentação bancária foi realizada.")
            return redirect(record_return_url(profile, route))
    return render(request, "finance/object_form.html", {
        "form": form, "object": instance, "profile": profile, "workspace": profile.workspace,
        "title": f"{'Editar' if instance else 'Cadastrar'} {label}",
        "cancel_url": record_return_url(profile, route),
        "delete_url": reverse(f"finance:{kind}-delete", args=[profile.pk, object_id])
            if object_id and kind != "reserve" else None,
    })


@login_required
@require_http_methods(["GET", "POST"])
def record_delete(request, profile_id, kind, object_id):
    profile = editable_profile(request.user, profile_id)
    model, _, label, route = record_config(kind)
    instance = get_object_or_404(model, pk=object_id, profile=profile)
    error = None
    if request.method == "POST":
        if request.POST.get("confirm") != "yes":
            error = "Confirme a exclusão para continuar."
        else:
            try:
                delete_record(request.user, profile.pk, model, object_id)
            except ValidationError as exc:
                error = " ".join(exc.messages)
            else:
                messages.success(request, "Cadastro excluído.")
                return redirect(record_return_url(profile, route))
    return render(request, "finance/confirm_delete.html", {
        "object": instance, "workspace": profile.workspace, "title": f"Excluir {label}",
        "cancel_url": reverse(f"finance:{kind}-edit", args=[profile.pk, object_id]), "error": error,
    }, status=400 if error else 200)


def workspace_selection(request, workspace_id):
    require_workspace_access(request.user, workspace_id)
    workspace = get_object_or_404(Workspace, pk=workspace_id)
    available = get_accessible_profiles(request.user).filter(workspace=workspace, is_archived=False).order_by("pk")
    form = WorkspaceFilterForm(request.GET, profiles=available)
    if not form.is_valid():
        return workspace, form, [], None
    selected = form.cleaned_data["profiles"]
    return workspace, form, selected if selected.exists() else available, form.cleaned_data["month"]


@login_required
@require_http_methods(["GET"])
def workspace_page(request, workspace_id, section="overview"):
    from decimal import Decimal
    from apps.finance.domain.planning import monthly_due_date

    workspace, filter_form, profiles, month = workspace_selection(request, workspace_id)
    if month is None:
        return render(request, "finance/workspace_page.html", {
            "workspace": workspace, "filter_form": filter_form, "active_nav": section,
            "title": "Filtro inválido", "sections": [],
        }, status=400)
    sections = []
    for profile in profiles:
        item = {"profile": profile, "summary": profile_summary(profile, month),
                "can_edit": user_can_edit_profile(request.user, profile.pk),
                "can_admin": user_is_workspace_admin(request.user, workspace.pk)}
        if section == "expenses":
            recurring = list(RecurringExpense.objects.filter(profile=profile).order_by("due_day", "pk"))
            for expense in recurring:
                expense.due_on = monthly_due_date(month, expense.due_day)
            item["recurring"] = recurring
            item["unexpected"] = UnexpectedExpense.objects.filter(
                profile=profile, recorded_on__year=month.year, recorded_on__month=month.month,
            ).order_by("-recorded_on", "pk")
        if section == "investments":
            item["investments"] = InvestmentPosition.objects.filter(profile=profile).order_by("category", "pk")
        sections.append(item)
    known_income = sum((s["summary"]["income"] for s in sections if s["summary"]["income"] is not None), Decimal("0"))
    context = {
        "workspace": workspace, "filter_form": filter_form, "sections": sections,
        "active_nav": section, "month": month,
        "title": {"overview": "Visão geral", "expenses": "Despesas", "investments": "Investimentos"}[section],
        "known_income": known_income,
        "unknown_income_count": sum(s["summary"]["income"] is None for s in sections),
        "bank_balance": sum((s["summary"]["bank_balance"] for s in sections), Decimal("0")),
        "bank_unknown_count": sum(s["summary"]["bank_unknown_count"] for s in sections),
    }
    return render(request, "finance/workspace_page.html", context)
