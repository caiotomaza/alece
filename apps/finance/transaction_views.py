# SPDX-License-Identifier: GPL-3.0-only
"""Authenticated transaction forms; services perform all money writes."""
from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from apps.core.permissions import require_module, user_can_module
from apps.finance.models import (
    InvestmentPosition, RecurringExpense, TransactionBatch, UnexpectedExpense,
)
from apps.finance.services.ledger import (
    confirm_outflow, reverse_batch, reverse_item_payments, transfer, withdraw_investment,
)
from apps.finance.services.monthly import (
    application_due, paid_for_application, paid_for_recurring,
    paid_for_unexpected, recurring_due,
)
from apps.finance.transaction_forms import PaymentForm, TransferForm, WithdrawalForm


def _month(request):
    value = request.POST.get("month") if request.method == "POST" else request.GET.get("month")
    if not value:
        return timezone.localdate().replace(day=1)
    try:
        month = date.fromisoformat(f"{value}-01")
    except ValueError:
        return None
    return month if month.strftime("%Y-%m") == value else None


def _return_url(profile, kind, month=None, monthly_mode=False):
    if kind == "application" and not monthly_mode or kind == "withdrawal":
        return reverse("finance:investments", args=[profile.workspace_id])
    if kind == "transfer":
        return reverse("finance:movements", args=[profile.workspace_id])
    suffix = f"?month={month:%Y-%m}" if month else ""
    return reverse("finance:overview", args=[profile.workspace_id]) + suffix


def _splits(selected, amount):
    remaining = amount
    allocations = {}
    for account in selected.order_by("pk"):
        used = min(remaining, account.balance or Decimal("0.00"))
        if used > 0:
            allocations[account.pk] = used
            remaining -= used
        if remaining == 0:
            break
    return allocations if remaining == 0 else None


@login_required
@require_http_methods(["GET", "POST"])
def payment(request, profile_id, kind, object_id):
    if kind not in {"recurring", "unexpected", "application"}:
        return HttpResponseBadRequest("Tipo inválido.")
    module = "investments" if kind == "application" else "expenses"
    profile = require_module(request.user, profile_id, module, "edit")
    require_module(request.user, profile_id, "movements", "edit")
    require_module(request.user, profile_id, "accounts", "view")
    monthly_mode = (request.POST.get("plan") if request.method == "POST" else
                    request.GET.get("plan")) == "1"
    if kind == "recurring":
        obj = get_object_or_404(RecurringExpense, pk=object_id, profile=profile, is_active=True)
        month = _month(request)
        if month is None:
            return HttpResponseBadRequest("Competência inválida.")
        due = recurring_due(obj, month)
        paid = paid_for_recurring(obj, month)
    elif kind == "unexpected":
        obj = get_object_or_404(UnexpectedExpense, pk=object_id, profile=profile)
        month = obj.recorded_on.replace(day=1)
        due, paid = obj.amount, paid_for_unexpected(obj)
    else:
        obj = get_object_or_404(InvestmentPosition, pk=object_id, profile=profile, is_active=True)
        month = _month(request)
        if month is None:
            return HttpResponseBadRequest("Competência inválida.")
        if monthly_mode:
            require_module(request.user, profile_id, "overview", "view")
            require_module(request.user, profile_id, "expenses", "view")
            if month != timezone.localdate().replace(day=1):
                return HttpResponseBadRequest("Aplicação mensal exige o mês atual.")
            due, plan = application_due(obj, month)
            paid = paid_for_application(plan)
            if due <= 0:
                messages.info(request, "Não há aplicação mensal sugerida para esta posição.")
                return redirect(_return_url(profile, kind, month, monthly_mode=True))
        else:
            due, paid = None, Decimal("0.00")
    remaining = max(Decimal("0.00"), due - paid) if due is not None else None
    if remaining == 0:
        messages.info(request, "Este item já está quitado.")
        return redirect(_return_url(profile, kind, month, monthly_mode=monthly_mode))
    form = PaymentForm(
        request.POST if request.method == "POST" else None,
        profile=profile, remaining=remaining,
        initial={"idempotency_key": uuid4().hex},
    )
    if request.method == "POST" and form.is_valid():
        amount = form.cleaned_data["amount"]
        splits = _splits(form.cleaned_data["accounts"], amount)
        if splits is None:
            form.add_error("accounts", "Selecione saldos suficientes para cobrir o valor.")
        else:
            links = {
                "recurring_expense_id": obj.pk if kind == "recurring" else None,
                "unexpected_expense_id": obj.pk if kind == "unexpected" else None,
                "investment_id": obj.pk if kind == "application" else None,
            }
            try:
                confirm_outflow(
                    actor=request.user, profile_id=profile.pk, kind=kind, splits=splits,
                    idempotency_key=form.cleaned_data["idempotency_key"],
                    competence_month=month if kind == "recurring" or monthly_mode else None,
                    note=obj.name, **links,
                )
            except ValidationError as error:
                form.add_error(None, error)
            else:
                messages.success(request, "Movimentação confirmada e saldos atualizados.")
                return redirect(_return_url(profile, kind, month, monthly_mode=monthly_mode))
    return render(request, "finance/payment_form.html", {
        "workspace": profile.workspace, "profile": profile, "object": obj,
        "kind": kind, "month": month, "remaining": remaining, "form": form,
        "monthly_mode": monthly_mode,
        "cancel_url": _return_url(profile, kind, month, monthly_mode=monthly_mode),
    })


@login_required
@require_POST
def reverse_item(request, profile_id, kind, object_id):
    module = "investments" if kind == "application" else "expenses"
    profile = require_module(request.user, profile_id, module, "edit")
    month = _month(request)
    if month is None or kind not in {"recurring", "unexpected", "application"}:
        return HttpResponseBadRequest("Item ou competência inválida.")
    model = {"recurring": RecurringExpense, "unexpected": UnexpectedExpense,
             "application": InvestmentPosition}[kind]
    get_object_or_404(model, pk=object_id, profile=profile)
    try:
        reverse_item_payments(
            actor=request.user, profile_id=profile.pk, kind=kind, object_id=object_id,
            competence_month=month, idempotency_key=request.POST.get("idempotency_key", ""),
        )
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    else:
        messages.success(request, "Pagamentos estornados; o histórico foi preservado.")
    return redirect(_return_url(profile, kind, month, monthly_mode=kind == "application"))


@login_required
@require_http_methods(["GET", "POST"])
def transfer_view(request, profile_id):
    profile = require_module(request.user, profile_id, "movements", "edit")
    require_module(request.user, profile_id, "accounts", "view")
    form = TransferForm(
        request.POST if request.method == "POST" else None, profile=profile,
        initial={"idempotency_key": uuid4().hex},
    )
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            transfer(
                actor=request.user, profile_id=profile.pk, source_id=data["source"].pk,
                destination_id=data["destination"].pk, amount=data["amount"],
                note=data["note"], idempotency_key=data["idempotency_key"],
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Transferência registrada sem classificar receita ou despesa.")
            return redirect(_return_url(profile, "transfer"))
    return render(request, "finance/transaction_form.html", {
        "workspace": profile.workspace, "profile": profile, "title": "Transferir entre contas",
        "form": form, "cancel_url": _return_url(profile, "transfer"),
    })


@login_required
@require_http_methods(["GET", "POST"])
def withdrawal(request, profile_id, investment_id):
    profile = require_module(request.user, profile_id, "investments", "edit")
    require_module(request.user, profile_id, "movements", "edit")
    require_module(request.user, profile_id, "accounts", "view")
    position = get_object_or_404(
        InvestmentPosition, pk=investment_id, profile=profile, is_active=True,
    )
    form = WithdrawalForm(
        request.POST if request.method == "POST" else None,
        profile=profile, position=position, initial={"idempotency_key": uuid4().hex},
    )
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            withdraw_investment(
                actor=request.user, profile_id=profile.pk, investment_id=position.pk,
                destination_id=data["destination"].pk, amount=data["amount"],
                idempotency_key=data["idempotency_key"],
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Resgate registrado e posição atualizada.")
            return redirect(_return_url(profile, "withdrawal"))
    return render(request, "finance/transaction_form.html", {
        "workspace": profile.workspace, "profile": profile, "title": f"Resgatar · {position.name}",
        "form": form, "cancel_url": _return_url(profile, "withdrawal"),
    })


@login_required
@require_http_methods(["GET"])
def movement_detail(request, profile_id, batch_id):
    profile = require_module(request.user, profile_id, "movements", "view")
    batch = get_object_or_404(
        TransactionBatch.objects.select_related(
            "created_by", "reversal_of",
            "recurring_expense", "unexpected_expense", "investment",
        ),
        pk=batch_id, profile=profile,
    )
    can_edit = user_can_module(request.user, profile_id, "movements", "edit")
    is_reversible = can_edit and not batch.reversal_of_id and not hasattr(batch, "reversal")

    legs = list(batch.legs.select_related("account").order_by("pk"))
    accounts_display = ", ".join(f"{leg.account.name} (R$ {leg.delta:+.2f})" for leg in legs)
    if not accounts_display:
        accounts_display = "—"

    status_display = "Confirmado"
    if batch.reversal_of_id:
        status_display = "Estorno"
    elif hasattr(batch, "reversal"):
        status_display = "Estornado"

    return render(request, "finance/movement_detail.html", {
        "workspace": profile.workspace,
        "profile": profile,
        "batch": batch,
        "legs": legs,
        "accounts_display": accounts_display,
        "status_display": status_display,
        "can_reverse": is_reversible,
        "can_edit": can_edit,
        "reversal_key": uuid4().hex,
        "cancel_url": reverse("finance:movements", args=[profile.workspace_id]),
    })


@login_required
@require_POST
def reverse_movement(request, profile_id, batch_id):
    profile = require_module(request.user, profile_id, "movements", "edit")
    try:
        reverse_batch(
            actor=request.user, profile_id=profile.pk, batch_id=batch_id,
            idempotency_key=request.POST.get("idempotency_key", "") or uuid4().hex,
        )
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    else:
        messages.success(request, "Estorno registrado no histórico.")
    return redirect("finance:movements", workspace_id=profile.workspace_id)

