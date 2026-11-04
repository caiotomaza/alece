# SPDX-License-Identifier: GPL-3.0-only
from django import forms
from django.http import Http404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from uuid import uuid4

from apps.core.permissions import (
    get_accessible_profiles, get_module_profiles, require_module, require_profile_view,
    require_workspace_access, require_workspace_admin, user_can_module, user_is_workspace_admin,
)
from apps.finance.forms import BankAccountForm, FinancialProfileForm
from apps.finance.models import (
    BankAccount, FinancialProfile, InvestmentPosition, LedgerLeg, RecurringExpense, ReservePolicy,
    TransactionBatch, UnexpectedExpense, Workspace,
)
from apps.finance.query_forms import IncomeForm, WorkspaceFilterForm
from apps.finance.services.metrics import aggregate_income_plan, monthly_activity, profile_summary
from apps.finance.services.monthly import monthly_items
from apps.finance.services.records import delete_record, save_record, update_income
from apps.finance.profile_selection import selected_profile_id
from apps.finance.services.profiles import update_financial_profile
from apps.finance.services.profiles import create_financial_profile


MONTHLY_ITEM_LABELS = {
    "recurring": "Previsível",
    "unexpected": "Imprevisível",
    "application": "Aplicação",
}


def add_validation_errors(form, error):
    if hasattr(error, "error_dict"):
        for field, errors in error.error_dict.items():
            form.add_error(field if field in form.fields else None, errors)
    else:
        form.add_error(None, error)


@login_required
@require_http_methods(["GET"])
def profile_list(request, workspace_id):
    """Backward-compatible finance URL uses the same role-restricted settings UI."""
    require_workspace_access(request.user, workspace_id)
    request.session["alece_workspace_id"] = workspace_id
    from apps.core.settings_views import settings_dashboard
    return settings_dashboard(request, workspace_id)


# As ações de cadastro sempre exigem perfil único, inclusive ao visualizar "Todos".
# Escolher o destino não altera a preferência de navegação da sessão.
PROFILE_OPERATION_MAP = {
    "income": ("overview", "finance:income-edit", "Editar renda mensal"),
    "account": ("accounts", "finance:account-create", "Adicionar conta"),
    "recurring": ("expenses", "finance:recurring-create", "Adicionar despesa previsível"),
    "unexpected": ("expenses", "finance:unexpected-create", "Adicionar despesa imprevisível"),
    "investment": ("investments", "finance:investment-create", "Adicionar investimento"),
    "transfer": ("movements", "finance:transfer", "Nova transferência"),
}


@login_required
@require_http_methods(["GET", "POST"])
def choose_profile_for_action(request, workspace_id, operation):
    """Render the destination form directly, with an authorized profile dropdown.

    Keep the old named URL as a compatibility alias; it no longer renders a
    separate profile-picker page. The sidebar's viewing filter is unaffected.
    """
    workspace = require_workspace_access(request.user, workspace_id)
    if operation not in PROFILE_OPERATION_MAP:
        raise Http404("Operação desconhecida.")
    if operation == "income":
        return redirect("finance:income-bulk", workspace_id=workspace_id)
    if operation == "transfer":
        from apps.finance.transaction_views import transfer_view
        return transfer_view(request, workspace_id=workspace_id)

    module, _, title = PROFILE_OPERATION_MAP[operation]
    available = get_module_profiles(request.user, module, "edit").filter(
        workspace_id=workspace_id, is_archived=False,
    ).order_by("name", "pk")
    if not available.exists():
        raise PermissionDenied("Nenhum perfil autorizado para esta operação.")

    model, form_class, _, route = record_config(operation)
    form = form_class(request.POST if request.method == "POST" else None)
    for field in ("is_archived", "is_active"):
        form.fields.pop(field, None)
    form.fields = {
        "profile_id": forms.ModelChoiceField(
            queryset=available, label="Perfil financeiro",
            empty_label="Selecione um perfil financeiro", required=True,
        ), **form.fields,
    }
    explicit_id = request.GET.get("profile_id")
    if explicit_id is None:
        explicit_id = selected_profile_id(request, workspace_id)
    if request.method == "GET" and explicit_id is not None and str(explicit_id).isdigit():
        profile = available.filter(pk=explicit_id).first()
        if profile is not None:
            form.initial["profile_id"] = profile.pk

    if request.method == "POST" and form.is_valid():
        profile = form.cleaned_data.pop("profile_id")
        # Re-check authorization after form validation; the service also checks
        # permissions and locks before persistence.
        editable_profile(request.user, profile.pk, module)
        if profile.workspace_id != workspace_id:
            raise PermissionDenied("Perfil de outro núcleo.")
        try:
            save_record(request.user, profile.pk, model, form.cleaned_data)
        except ValidationError as error:
            add_validation_errors(form, error)
        else:
            messages.success(request, "Cadastro salvo. Nenhuma movimentação bancária foi realizada.")
            if operation == "account" and request.GET.get("return") == "profile":
                return redirect("finance:profile-detail", profile_id=profile.pk)
            return redirect(record_return_url(profile, route))

    cancel_url = reverse({
        "account": "visao-geral", "recurring": "despesas",
        "unexpected": "despesas", "investment": "investimentos",
    }[operation])
    if operation == "account" and request.GET.get("return") == "profile":
        from_id = request.GET.get("profile_id", "")
        from_profile = available.filter(pk=from_id).first() if from_id.isdigit() else None
        if from_profile:
            cancel_url = reverse("finance:profile-detail", args=[from_profile.pk])
    return render(request, "finance/object_form.html", {
        "workspace": workspace, "form": form, "title": title,
        "cancel_url": cancel_url, "active_nav": {
            "account": "overview", "recurring": "expenses",
            "unexpected": "expenses", "investment": "investments",
        }[operation],
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
            return redirect("configuracoes-perfis")
    return render(request, "finance/object_form.html", {
        "workspace": workspace, "form": form, "title": "Novo perfil financeiro",
        "cancel_url": reverse("configuracoes-perfis"),
    })


@login_required
@require_http_methods(["GET"])
def profile_detail(request, profile_id):
    profile = require_profile_view(request.user, profile_id)
    can_accounts_view = user_can_module(request.user, profile_id, "accounts")
    return render(request, "finance/profile_detail.html", {
        "profile": profile, "accounts": profile.accounts.order_by("pk") if can_accounts_view else [],
        "workspace": profile.workspace,
        "can_admin": user_is_workspace_admin(request.user, profile.workspace_id),
        "can_accounts_view": can_accounts_view,
        "can_accounts_edit": user_can_module(request.user, profile_id, "accounts", "edit") and not profile.is_archived,
        "can_overview_view": user_can_module(request.user, profile_id, "overview"),
        "can_overview_edit": user_can_module(request.user, profile_id, "overview", "edit") and not profile.is_archived,
    })


@login_required
@require_http_methods(["GET", "POST"])
def account_create(request, profile_id):
    profile = editable_profile(request.user, profile_id)
    form = BankAccountForm(request.POST if request.method == "POST" else None)
    form.fields.pop("is_archived", None)
    return_url = (reverse("finance:profile-detail", args=[profile.pk])
                  if request.GET.get("return") == "profile" else reverse("visao-geral"))
    if request.method == "POST" and form.is_valid():
        try:
            save_record(request.user, profile.pk, BankAccount, form.cleaned_data)
        except ValidationError as error:
            add_validation_errors(form, error)
        else:
            messages.success(request, "Conta criada.")
            # Retorno à gestão de saldos somente quando solicitado pela tela do perfil.
            # O fluxo público anterior e a preferência da sessão permanecem intactos.
            return redirect(return_url)
    return render(request, "finance/object_form.html", {
        "profile": profile, "workspace": profile.workspace, "form": form, "title": "Nova conta",
        "cancel_url": return_url,
    })


@login_required
@require_http_methods(["GET", "POST"])
def profile_edit(request, profile_id):
    profile = require_profile_view(request.user, profile_id)
    require_workspace_admin(request.user, profile.workspace_id)
    form = FinancialProfileForm(request.POST if request.method == "POST" else None, instance=profile)
    # Arquivamento/reativação é ação administrativa separada do cadastro.
    form.fields.pop("is_archived", None)
    if request.method == "POST" and form.is_valid():
        try:
            update_financial_profile(request.user, profile.pk, form.cleaned_data)
        except ValidationError as error:
            add_validation_errors(form, error)
        else:
            messages.success(request, "Perfil atualizado.")
            return redirect("configuracoes-perfis")
    return render(request, "finance/object_form.html", {
        "form": form, "title": "Editar perfil financeiro", "object": profile,
        "workspace": profile.workspace, "profile": profile,
        "cancel_url": reverse("configuracoes-perfis"),
    })


@login_required
@require_http_methods(["GET", "POST"])
def profile_manage(request, profile_id):
    """Single administrative modal: metadata, archive and per-member grants."""
    from apps.finance.forms import ProfileGrantForm
    from apps.finance.models import ProfileGrant, WorkspaceMembership
    from apps.finance.services.grants import GRANT_FIELDS, save_grant
    profile = get_object_or_404(FinancialProfile, pk=profile_id, deleted_at__isnull=True)
    require_workspace_admin(request.user, profile.workspace_id)
    workspace = profile.workspace
    action = request.POST.get("action", "profile") if request.method == "POST" else None
    profile_form = FinancialProfileForm(request.POST if action == "profile" else None, instance=profile)
    # Arquivamento apenas pela ação explícita; não reativar em salvamento de dados.
    profile_form.fields.pop("is_archived", None)
    members = list(WorkspaceMembership.objects.filter(
        workspace=workspace, role=WorkspaceMembership.Role.COMMON
    ).select_related("user").order_by("user__username"))
    grant_forms = []
    selected_member = None
    for member in members:
        existing = ProfileGrant.objects.filter(profile=profile, membership=member).first()
        active = action == "grant" and request.POST.get("membership_id") == str(member.pk)
        grant_form = ProfileGrantForm(request.POST if active else None,
                                      instance=existing, prefix=f"grant_{member.pk}")
        grant_forms.append({"membership": member, "form": grant_form})
        if active:
            selected_member = (member, grant_form)
    if request.method == "POST":
        if action == "profile" and profile_form.is_valid():
            try:
                update_financial_profile(request.user, profile.pk, profile_form.cleaned_data)
            except ValidationError as error:
                add_validation_errors(profile_form, error)
            else:
                messages.success(request, "Perfil financeiro atualizado.")
                return redirect("configuracoes-perfis")
        elif action == "delete_profile":
            try:
                from apps.finance.services.profiles import delete_financial_profile
                delete_financial_profile(request.user, profile.pk, request.POST.get("confirm_deletion", ""))
            except ValidationError as error:
                add_validation_errors(profile_form, error)
            else:
                messages.success(request, "Perfil excluído da operação; histórico e auditoria preservados.")
                return redirect("configuracoes-perfis")
        elif action == "toggle_archive":
            try:
                update_financial_profile(request.user, profile.pk, {
                    "name": profile.name, "emoji": profile.emoji,
                    "monthly_income": profile.monthly_income,
                    "is_archived": not profile.is_archived,
                })
            except ValidationError as error:
                add_validation_errors(profile_form, error)
            else:
                messages.success(request, "Perfil reativado." if profile.is_archived else "Perfil arquivado; histórico preservado.")
                return redirect("configuracoes-perfis")
        elif action == "grant" and selected_member:
            member, grant_form = selected_member
            if grant_form.is_valid():
                try:
                    save_grant(actor=request.user, profile_id=profile.pk,
                               membership_id=member.pk,
                               levels={field: grant_form.cleaned_data[field] for field in GRANT_FIELDS})
                except ValidationError as error:
                    add_validation_errors(grant_form, error)
                else:
                    messages.success(request, "Permissões do perfil atualizadas.")
                    return redirect("configuracoes-perfis")
        else:
            if action not in ("profile", "grant", "toggle_archive", "delete_profile") or (action == "grant" and not selected_member):
                raise PermissionDenied("Ação administrativa inválida")
    # Interface antecipatória. A proteção real sempre ocorre nos serviços com lock.
    active_profiles = FinancialProfile.objects.filter(
        workspace=workspace, is_archived=False, deleted_at__isnull=True,
    )
    can_remove_profile = active_profiles.exclude(pk=profile.pk).exists()
    return render(request, "finance/profile_manage.html", {
        "profile": profile, "workspace": workspace, "form": profile_form,
        "grant_forms": grant_forms, "title": f"Gerenciar perfil: {profile.name}",
        "can_remove_profile": can_remove_profile,
        "active_profiles_count": active_profiles.count(),
        "cancel_url": reverse("configuracoes-perfis"),
    })


def editable_profile(user, profile_id, module="accounts"):
    profile = require_module(user, profile_id, module, "edit")
    if profile.is_archived:
        raise PermissionDenied("Perfil arquivado: reative antes de alterar seus cadastros.")
    return profile


@login_required
@require_http_methods(["GET", "POST"])
def income_edit(request, profile_id):
    profile = editable_profile(request.user, profile_id, "overview")
    form = IncomeForm(request.POST if request.method == "POST" else None,
                      initial={"monthly_income": profile.monthly_income})
    if request.method == "POST" and form.is_valid():
        try:
            update_income(request.user, profile.pk, form.cleaned_data["monthly_income"])
        except ValidationError as error:
            add_validation_errors(form, error)
        else:
            messages.success(request, "Renda atualizada. Nenhuma movimentação bancária foi realizada.")
            return redirect("visao-geral")
    return render(request, "finance/object_form.html", {
        "form": form, "title": "Editar renda mensal", "workspace": profile.workspace,
        "profile": profile,
        "cancel_url": reverse("visao-geral"),
    })


def _income_bulk_rows(profiles, data=None):
    """One validated IncomeForm per authorized profile; no implicit field sharing."""
    rows = []
    for profile in profiles:
        income_form = IncomeForm(data, prefix=f"income_{profile.pk}",
                                 initial={"monthly_income": profile.monthly_income})
        income_form.fields["monthly_income"].widget = forms.TextInput(attrs={
            "inputmode": "decimal", "autocomplete": "off",
            "aria-describedby": f"income_{profile.pk}-monthly_income_error",
        })
        rows.append({"profile": profile, "form": income_form})
    return rows


@login_required
@require_http_methods(["GET", "POST"])
def income_bulk_edit(request, workspace_id):
    """Edit income for authorized profiles in one atomic request.

    Normal Django form submission is the no-JavaScript fallback. JSON is used
    only for the dashboard's progressive enhancement, never for authorization.
    """
    workspace = require_workspace_access(request.user, workspace_id)
    wants_json = request.headers.get("Accept", "").startswith("application/json")
    allowed = list(get_module_profiles(request.user, "overview", "edit").filter(
        workspace_id=workspace_id, is_archived=False,
    ).order_by("pk"))
    if not allowed:
        raise PermissionDenied("Nenhum perfil financeiro autorizado para edição de renda.")

    def render_form(rows, *, status=200, alert=""):
        if wants_json:
            field_errors = {}
            for row in rows:
                field = row["form"]["monthly_income"]
                if field.errors:
                    field_errors[field.html_name] = [str(error) for error in field.errors]
            return JsonResponse({"ok": False, "message": alert or "Revise os valores informados.",
                                 "field_errors": field_errors}, status=status)
        return render(request, "finance/income_bulk_edit.html", {
            "workspace": workspace, "income_rows": rows, "alert": alert,
            "income_profile_ids": ",".join(str(profile.pk) for profile in allowed),
            "active_nav": "overview",
            "nav_profiles": list(get_accessible_profiles(request.user).filter(
                workspace_id=workspace_id, is_archived=False,
            ).order_by("pk")),
        }, status=status)

    if request.method == "GET":
        return render_form(_income_bulk_rows(allowed))

    # Detect concurrent access/profile changes; never erase a profile that was
    # not present when the user opened the form.
    expected_ids = ",".join(str(profile.pk) for profile in allowed)
    if request.POST.get("profile_ids") != expected_ids or any(
        f"income_{profile.pk}-monthly_income" not in request.POST for profile in allowed
    ):
        return render_form(_income_bulk_rows(allowed), status=409,
                           alert="A lista de perfis foi modificada. Reabra o formulário antes de salvar.")
    rows = _income_bulk_rows(allowed, request.POST)
    validities = [row["form"].is_valid() for row in rows]
    if not all(validities):
        # Evaluate every field rather than short-circuiting at the first error.
        return render_form(rows, status=422)
    try:
        with transaction.atomic():
            # Recheck privileges at write time and lock all rows in stable order.
            locked = list(FinancialProfile.objects.select_for_update().filter(
                pk__in=[profile.pk for profile in allowed], workspace_id=workspace_id,
                deleted_at__isnull=True, is_archived=False,
            ).order_by("pk"))
            if len(locked) != len(allowed) or any(
                not user_can_module(request.user, profile.pk, "overview", "edit")
                for profile in locked
            ):
                raise PermissionDenied("As permissões foram modificadas. Reabra o formulário.")
            for row, profile in zip(rows, locked):
                new_income = row["form"].cleaned_data["monthly_income"]
                if profile.monthly_income != new_income:
                    # Existing service verifies privileges and records redacted audit events.
                    update_income(request.user, profile.pk, new_income)
    except ValidationError as error:
        return render_form(rows, status=409, alert="Não foi possível salvar. Revise os perfis e tente novamente.")

    if wants_json:
        return JsonResponse({"ok": True, "message": "Rendas atualizadas."})
    messages.success(request, "Rendas atualizadas. Nenhuma movimentação financeira foi realizada.")
    return redirect("visao-geral")


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
    # O destino público consulta a preferência já validada na sessão. O perfil
    # editado é definido pelo endpoint, nunca pela seleção do menu.
    names = {"profile-detail": "visao-geral", "expenses": "despesas", "investments": "investimentos"}
    return reverse(names[route])


@login_required
@require_http_methods(["GET", "POST"])
def record_edit(request, profile_id, kind, object_id=None):
    module = {"account": "accounts", "recurring": "expenses", "unexpected": "expenses",
              "investment": "investments", "reserve": "investments"}[kind]
    profile = editable_profile(request.user, profile_id, module)
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
            if kind == "account" and request.GET.get("return") == "profile":
                return redirect("finance:profile-detail", profile_id=profile.pk)
            return redirect(record_return_url(profile, route))
    return_url = (reverse("finance:profile-detail", args=[profile.pk])
                  if kind == "account" and request.GET.get("return") == "profile"
                  else record_return_url(profile, route))
    delete_url = (reverse(f"finance:{kind}-delete", args=[profile.pk, object_id])
                  if object_id and kind != "reserve" else None)
    if kind == "account" and delete_url and request.GET.get("return") == "profile":
        delete_url += "?return=profile"
    return render(request, "finance/object_form.html", {
        "form": form, "object": instance, "profile": profile, "workspace": profile.workspace,
        "title": f"{'Editar' if instance else 'Adicionar'} {label}",
        "cancel_url": return_url, "delete_url": delete_url,
    })


@login_required
@require_http_methods(["GET", "POST"])
def record_delete(request, profile_id, kind, object_id):
    module = {"account": "accounts", "recurring": "expenses", "unexpected": "expenses",
              "investment": "investments"}[kind]
    profile = editable_profile(request.user, profile_id, module)
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
                if kind == "account" and request.GET.get("return") == "profile":
                    return redirect("finance:profile-detail", profile_id=profile.pk)
                return redirect(record_return_url(profile, route))
    cancel_url = reverse(f"finance:{kind}-edit", args=[profile.pk, object_id])
    if kind == "account" and request.GET.get("return") == "profile":
        cancel_url += "?return=profile"
    return render(request, "finance/confirm_delete.html", {
        "object": instance, "workspace": profile.workspace, "title": f"Excluir {label}",
        "cancel_url": cancel_url, "error": error,
    }, status=400 if error else 200)


def workspace_selection(request, workspace_id, section):
    """Navegação conserva a escolha por sessão sem aumentar permissões entre módulos.

    ?profiles=all limpa a preferência. Perfis sem direito ao módulo permanecem
    selecionados na barra, mas não produzem dados de outros perfis como fallback.
    """
    from apps.finance.profile_selection import remember_profile, selected_profile_id
    require_workspace_access(request.user, workspace_id)
    workspace = get_object_or_404(Workspace, pk=workspace_id)
    eligible = get_accessible_profiles(request.user).filter(
        workspace=workspace, is_archived=False,
    ).order_by("pk").distinct()
    module_allowed = get_module_profiles(request.user, section).filter(
        workspace=workspace, is_archived=False,
    ).order_by("pk").distinct()
    parameters = request.GET.copy()
    explicit = "profiles" in request.GET
    if explicit and request.GET.getlist("profiles") == ["all"]:
        parameters.pop("profiles", None)
        remember_profile(request, workspace_id, None)
    elif explicit:
        # Validate against all accessible profiles, even if their current module
        # has no permission; never silently replace a denied profile with all.
        candidate_form = WorkspaceFilterForm(parameters, profiles=eligible)
        if not candidate_form.is_valid():
            return workspace, candidate_form, module_allowed.none(), None
        choices = list(candidate_form.cleaned_data["profiles"].values_list("pk", flat=True))
        remember_profile(request, workspace_id, choices[0] if len(choices) == 1 else None)
    else:
        previous = selected_profile_id(request, workspace_id)
        if previous is not None:
            if eligible.filter(pk=previous).exists():
                parameters.setlist("profiles", [str(previous)])
            else:
                # Perfil arquivado, excluído ou sem autorização: descartar.
                remember_profile(request, workspace_id, None)
    form = WorkspaceFilterForm(parameters, profiles=eligible)
    if not form.is_valid():
        return workspace, form, module_allowed.none(), None
    selected = form.cleaned_data["profiles"]
    selected_ids = list(selected.values_list("pk", flat=True))
    profiles = module_allowed.filter(pk__in=selected_ids) if selected_ids else module_allowed
    return workspace, form, profiles, form.cleaned_data["month"]


@login_required
@require_http_methods(["GET"])
def workspace_page(request, workspace_id, section="overview"):
    from decimal import Decimal
    from apps.finance.domain.planning import monthly_due_date

    workspace, filter_form, profiles, month = workspace_selection(request, workspace_id, section)
    if month is None:
        return render(request, "finance/workspace_page.html", {
            "workspace": workspace, "filter_form": filter_form, "active_nav": section,
            "title": "Filtro inválido", "sections": [],
        }, status=400)
    sections = []
    for profile in profiles:
        module_rights = {module: user_can_module(request.user, profile.pk, module)
                         for module in ("accounts", "expenses", "investments", "movements")}
        summary = profile_summary(
                    profile, month,
                    include_accounts=module_rights["accounts"],
                    include_expenses=module_rights["expenses"],
                    include_investments=module_rights["investments"],
                    include_income=user_can_module(request.user, profile.pk, "overview"),
                ) if section != "movements" else {}
        item = {"profile": profile, "summary": summary,
                "can_edit": user_can_module(request.user, profile.pk, section, "edit"),
                "can_admin": user_is_workspace_admin(request.user, workspace.pk)}
        item.update({f"can_{module}_view": allowed for module, allowed in module_rights.items()})
        item["can_expenses_edit"] = user_can_module(
            request.user, profile.pk, "expenses", "edit",
        )
        item["can_investments_edit"] = user_can_module(
            request.user, profile.pk, "investments", "edit",
        )
        item["can_movements_edit"] = user_can_module(
            request.user, profile.pk, "movements", "edit",
        )
        item["can_accounts_edit"] = user_can_module(
            request.user, profile.pk, "accounts", "edit",
        )
        if section == "overview" and module_rights["expenses"]:
            items = monthly_items(
                profile, month,
                include_applications=(module_rights["investments"] and
                                      month == timezone.localdate().replace(day=1)),
                summary=summary,
            )
            for row in items:
                row["kind_label"] = MONTHLY_ITEM_LABELS.get(
                    row["kind"], "Tipo não identificado",
                )
                row["reversal_key"] = uuid4().hex
                row["can_edit"] = (item["can_investments_edit"] if row["kind"] == "application"
                                   else item["can_expenses_edit"])
                row["can_pay"] = (row["can_edit"] and item["can_movements_edit"]
                                  and module_rights["accounts"])
            item["monthly_items"] = items
            item["month_confirmed"] = (
                sum((row["paid"] for row in items if row["kind"] != "application"), Decimal("0"))
                + summary["applications_confirmed"]
            )
            item["month_pending"] = sum((row["remaining"] for row in items), Decimal("0"))
            item["projected_balance"] = (
                summary["bank_balance"] - item["month_pending"]
                if module_rights["accounts"] and profile.accounts.filter(
                    is_archived=False, balance__isnull=False,
                ).exists() else None
            )
        if section == "overview" and module_rights["accounts"]:
            item["accounts"] = profile.accounts.filter(is_archived=False).order_by("pk")
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
        if section == "movements":
            item["movements"] = list(LedgerLeg.objects.filter(
                batch__profile=profile,
            ).select_related("batch", "batch__created_by", "batch__reversal", "account").order_by(
                "-batch__occurred_on", "-batch_id", "pk",
            ))
            for leg in item["movements"]:
                leg.reversal_key = uuid4().hex
        sections.append(item)
    known_income = sum((s["summary"].get("income") for s in sections
                        if s["summary"].get("income") is not None), Decimal("0"))
    known_bank_sections = [
        s for s in sections
        if s.get("can_accounts_view") and s["summary"].get("bank_balance") is not None
    ]
    bank_balance = (
        sum((s["summary"]["bank_balance"] for s in known_bank_sections), Decimal("0"))
        if known_bank_sections else None
    )
    expense_sections = [s for s in sections if section != "movements" and s["can_expenses_view"]]
    investment_sections = [s for s in sections if section != "movements" and s["can_investments_view"]]
    movement_legs = [leg for item in sections for leg in item.get("movements", [])]
    movement_batches = {leg.batch_id: leg.batch for leg in movement_legs}.values()
    monthly_payment_batches = [batch for batch in movement_batches if (
        batch.occurred_on.year == month.year and batch.occurred_on.month == month.month
        and batch.kind in (TransactionBatch.Kind.RECURRING, TransactionBatch.Kind.UNEXPECTED)
        and not batch.reversal_of_id and not getattr(batch, "reversal", None)
    )]
    has_overview_data = any(
        item["summary"].get("income") is not None
        or (item["can_accounts_view"] and item["profile"].accounts.filter(is_archived=False).exists())
        or (item["can_expenses_view"] and (
            RecurringExpense.objects.filter(profile=item["profile"], is_active=True).exists()
            or UnexpectedExpense.objects.filter(profile=item["profile"]).exists()
        ))
        or (item["can_investments_view"] and InvestmentPosition.objects.filter(
            profile=item["profile"], is_active=True,
        ).exists())
        for item in sections
    ) if section == "overview" else False
    chart_category = request.GET.get("chart_category", "all")
    if chart_category not in {"all", "essential", "strategic", "discretionary", "unexpected"}:
        chart_category = "all"
    chart_profiles = [item["profile"].pk for item in sections]
    if section == "expenses":
        chart_series = monthly_activity(
            chart_profiles, month,
            kinds=(TransactionBatch.Kind.RECURRING, TransactionBatch.Kind.UNEXPECTED),
            category=chart_category,
        )
    elif section == "investments":
        chart_series = monthly_activity(
            [item["profile"].pk for item in sections if item["can_movements_view"]],
            month, kinds=(TransactionBatch.Kind.APPLICATION, TransactionBatch.Kind.WITHDRAWAL),
        )
    elif section == "movements":
        chart_series = monthly_activity(
            chart_profiles, month,
            kinds=tuple(kind for kind in TransactionBatch.Kind.values if kind != "reversal"),
        )
    else:
        chart_series = None
    expense_cards = [
        {"label": label, "total": sum(
            (s["summary"]["recurring_totals"][category] for s in expense_sections),
            Decimal("0"),
        )}
        for category, label in RecurringExpense.Category.choices
    ]
    expense_cards.append({
        "label": "Imprevisíveis",
        "total": sum((
            s["summary"]["unexpected_pending"] + s["summary"]["unexpected_confirmed"]
            for s in expense_sections
        ), Decimal("0")),
    })
    investment_cards = [
        {"label": label, "total": sum(
            (s["summary"]["investment_totals"][category] for s in investment_sections),
            Decimal("0"),
        )}
        for category, label in InvestmentPosition.Category.choices
    ]
    # O botão + deve permanecer disponível quando a visualização é Todos.
    # A escolha do destino é separada do filtro de leitura; nunca escolher
    # automaticamente o primeiro perfil para gravar dados.
    chosen_id = selected_profile_id(request, workspace_id)
    is_all_profiles = chosen_id is None

    def action_url(operation):
        module, _, _ = PROFILE_OPERATION_MAP[operation]
        possible = get_module_profiles(request.user, module, "edit").filter(
            workspace=workspace, is_archived=False,
        )
        if operation == "transfer":
            possible = possible.filter(pk__in=get_module_profiles(
                request.user, "accounts", "view",
            ).values("pk"))
        if not is_all_profiles:
            possible = possible.filter(pk=chosen_id)
        if not possible.exists():
            return None
        # One form with a selector; never a preliminary chooser modal.
        return reverse("finance:choose-profile-action", args=[workspace_id, operation])

    action_urls = {operation: action_url(operation) for operation in PROFILE_OPERATION_MAP}
    # Renda é editada em um único modal multi-perfil, sem tela intermediária.
    income_editable_profiles = list(get_module_profiles(
        request.user, "overview", "edit",
    ).filter(workspace_id=workspace_id, is_archived=False).order_by("pk")) if section == "overview" else []
    action_urls["income"] = (
        reverse("finance:income-bulk", args=[workspace_id])
        if income_editable_profiles else None
    ) if section == "overview" else action_urls["income"]
    import_profiles = [item["profile"] for item in sections if
                       item["can_movements_edit"] and item["can_accounts_view"]]
    import_selected = import_profiles[0] if not is_all_profiles and len(import_profiles) == 1 else None
    context = {
        "action_urls": action_urls,
        "income_rows": _income_bulk_rows(income_editable_profiles) if section == "overview" else [],
        "income_profile_ids": ",".join(str(profile.pk) for profile in income_editable_profiles),
        "import_profiles": import_profiles,
        "import_profile": import_selected,
        "all_profiles_selected": is_all_profiles,
        "workspace": workspace, "filter_form": filter_form, "sections": sections,
        "selected_profile_without_module_access": bool(
            filter_form.cleaned_data.get("profiles") and not sections
        ),
        "nav_profiles": list(get_accessible_profiles(request.user).filter(
            workspace=workspace, is_archived=False,
        ).order_by("pk")),
        "active_nav": section, "month": month,
        "title": {"overview": "Visão geral", "expenses": "Despesas", "investments": "Investimentos", "movements": "Movimentações", "settings": "Configurações"}[section],
        "known_income": known_income,
        "known_income_count": sum(s["summary"].get("income") is not None for s in sections),
        "unknown_income_count": sum(s["summary"].get("income") is None for s in sections),
        "bank_balance": bank_balance,
        "bank_unknown_count": sum(s["summary"].get("bank_unknown_count", 0) for s in sections),
        "bank_visible_count": sum(s.get("can_accounts_view", False) for s in sections),
        "expense_cards": expense_cards if expense_sections else [],
        "investment_cards": investment_cards if investment_sections else [],
        "income_plan": aggregate_income_plan(sections) if section == "overview" else None,
        "has_overview_data": has_overview_data,
        "movement_count": len({leg.batch_id for leg in movement_legs}),
        "movement_month_payments": sum((batch.amount for batch in monthly_payment_batches), Decimal("0"))
            if monthly_payment_batches else None,
        "movement_month_emergency": sum((
            batch.amount for batch in monthly_payment_batches
            if batch.kind == TransactionBatch.Kind.UNEXPECTED
        ), Decimal("0")) if monthly_payment_batches else None,
        "monthly_count": sum(len(item.get("monthly_items", [])) for item in sections),
        "recurring_count": sum(len(item.get("recurring", [])) for item in sections),
        "unexpected_count": sum(len(item.get("unexpected", [])) for item in sections),
        "investment_count": sum(len(item.get("investments", [])) for item in sections),
        "movement_credits": sum((leg.delta for leg in movement_legs if leg.delta > 0), Decimal("0")),
        "movement_debits": sum((-leg.delta for leg in movement_legs if leg.delta < 0), Decimal("0")),
        "has_import_access": bool(import_profiles),
        "chart_series": chart_series,
        "chart_category": chart_category,
    }
    if section in ("expenses", "investments", "movements"):
        from apps.core.models import AIAnalysis
        visible_ids = [item["profile"].pk for item in sections]
        latest = {}
        if visible_ids:
            for analysis in AIAnalysis.objects.filter(
                workspace=workspace, profile_id__in=visible_ids, section=section,
            ).select_related("profile").order_by("-created_at"):
                if analysis.profile_id not in latest:
                    latest[analysis.profile_id] = analysis
        context["ai_cards"] = list(latest.values())
    # Todas as seções devem devolver HttpResponse, inclusive "overview".
    # Não restrinja o retorno às seções que exibem cartões de IA.
    return render(request, "finance/workspace_page.html", context)
