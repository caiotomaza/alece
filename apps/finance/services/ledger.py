# SPDX-License-Identifier: GPL-3.0-only
"""Atomic, profile-scoped cash events and balanced journal entries.

Every public command validates the actor and locks the profile before linked rows.
The profile lock serializes payment limits, idempotency and account writes within it.
"""
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F, Sum
from django.utils import timezone

from apps.core.permissions import require_module
from apps.finance.domain.calculations import money
from apps.finance.models import (
    BankAccount, FinancialProfile, InvestmentPosition, JournalEntry, LedgerLeg,
    MonthlyExpense, MonthlyInvestmentPlan, RecurringExpense, TransactionBatch,
    UnexpectedExpense,
)

ZERO = Decimal("0.00")


def _locked_profile(actor, profile_id):
    require_module(actor, profile_id, "movements", "edit")
    profile = FinancialProfile.objects.select_for_update().get(pk=profile_id)
    if profile.is_archived:
        raise ValidationError("Perfil arquivado não aceita movimentações.")
    return profile


def _key(value):
    if not value or len(value) > 120:
        raise ValidationError("Chave idempotente obrigatória, com até 120 caracteres.")
    return value


def _amount(value):
    result = money(value)
    if result <= ZERO:
        raise ValidationError("O valor deve ser positivo.")
    return result


def _locked_accounts(profile_id, account_ids):
    rows = list(BankAccount.objects.select_for_update().filter(pk__in=sorted(account_ids)).order_by("pk"))
    if len(rows) != len(account_ids):
        raise ValidationError("Conta inexistente.")
    for account in rows:
        if account.profile_id != profile_id:
            raise ValidationError("Conta pertence a outro perfil financeiro.")
        if account.is_archived:
            raise ValidationError("Conta arquivada não aceita movimentações.")
        if account.balance is None:
            raise ValidationError("Saldo desconhecido não pode custear ou receber movimentações.")
        if account.opening_balance is None:
            raise ValidationError("Conta legada sem saldo inicial conciliado exige revisão antes de movimentar.")
    return {account.pk: account for account in rows}


def _apply_bank_deltas(batch, accounts, deltas):
    for account_id in sorted(deltas):
        delta = deltas[account_id]
        account = accounts[account_id]
        if account.balance + delta < ZERO:
            raise ValidationError(f"Saldo insuficiente: {account.name}.")
        BankAccount.objects.filter(pk=account_id).update(balance=F("balance") + delta)
        LedgerLeg.objects.create(batch=batch, account=account, delta=delta)


def _write_journal(batch, postings):
    """Postings are (account code, debit, credit, bank account or None)."""
    debits = sum((row[1] for row in postings), ZERO)
    credits = sum((row[2] for row in postings), ZERO)
    if debits != credits or debits <= ZERO:
        raise ValidationError("Lançamento contábil não balanceado.")
    JournalEntry.objects.bulk_create([
        JournalEntry(batch=batch, account_code=code, debit=debit, credit=credit,
                     bank_account=account)
        for code, debit, credit, account in postings
    ])


def _existing(key, expected):
    batch = TransactionBatch.objects.filter(idempotency_key=key).first()
    if batch is None:
        return None
    actual = (
        batch.created_by_id, batch.profile_id, batch.kind, batch.amount, batch.competence_month,
        batch.recurring_expense_id, batch.unexpected_expense_id, batch.investment_id,
        {leg.account_id: leg.delta for leg in batch.legs.all()},
    )
    if actual != expected:
        raise ValidationError("Chave idempotente reaproveitada com dados divergentes.")
    return batch


def _create_batch(**fields):
    try:
        with transaction.atomic():
            return TransactionBatch.objects.create(**fields)
    except IntegrityError as error:
        raise ValidationError("Operação concorrente ou chave idempotente já utilizada.") from error


def _active_paid(queryset):
    return queryset.filter(reversal__isnull=True).aggregate(total=Sum("amount"))["total"] or ZERO


@transaction.atomic
def confirm_outflow(
    *, actor, profile_id: int, kind: str, splits: dict[int, Decimal],
    idempotency_key: str, note: str = "", occurred_on: date | None = None,
    competence_month: date | None = None, recurring_expense_id: int | None = None,
    unexpected_expense_id: int | None = None, investment_id: int | None = None,
):
    if kind not in {"recurring", "unexpected", "application"}:
        raise ValidationError("Tipo inválido para saída de caixa.")
    _key(idempotency_key)
    if not splits:
        raise ValidationError("Informe ao menos uma conta de origem.")
    amounts = {int(pk): _amount(value) for pk, value in splits.items()}
    total = sum(amounts.values(), ZERO)
    if kind == "recurring":
        if not recurring_expense_id or unexpected_expense_id or investment_id:
            raise ValidationError("Vínculo de despesa previsível inválido.")
        if competence_month is None or competence_month.day != 1:
            raise ValidationError("Competência mensal inválida.")
    elif kind == "unexpected":
        if not unexpected_expense_id or recurring_expense_id or investment_id:
            raise ValidationError("Vínculo de despesa imprevisível inválido.")
    else:
        if not investment_id or recurring_expense_id or unexpected_expense_id:
            raise ValidationError("Aplicação exige investimento do mesmo perfil.")
        if competence_month is not None and (
            competence_month.day != 1 or competence_month != timezone.localdate().replace(day=1)
        ):
            raise ValidationError("Aplicação de Este mês exige a competência atual.")
    if kind in {"recurring", "unexpected"}:
        require_module(actor, profile_id, "expenses", "edit")
    else:
        require_module(actor, profile_id, "investments", "edit")
        if competence_month is not None:
            require_module(actor, profile_id, "overview", "view")
            require_module(actor, profile_id, "expenses", "view")
    require_module(actor, profile_id, "accounts", "view")
    _locked_profile(actor, profile_id)
    expense = None
    if kind == "unexpected":
        expense = UnexpectedExpense.objects.select_for_update().filter(
            pk=unexpected_expense_id, profile_id=profile_id,
        ).first()
        if expense is None:
            raise ValidationError("Despesa imprevisível de outro perfil.")
        competence_month = expense.recorded_on.replace(day=1)
    expected = (
        actor.pk, profile_id, kind, total, competence_month, recurring_expense_id,
        unexpected_expense_id, investment_id,
        {account_id: -amount for account_id, amount in amounts.items()},
    )
    existing = _existing(idempotency_key, expected)
    if existing:
        return existing
    monthly = None
    monthly_plan = None
    position = None
    if kind == "recurring":
        expense = RecurringExpense.objects.select_for_update().filter(
            pk=recurring_expense_id, profile_id=profile_id, is_active=True,
        ).first()
        if expense is None:
            raise ValidationError("Despesa previsível inexistente ou inativa neste perfil.")
        monthly, _ = MonthlyExpense.objects.select_for_update().get_or_create(
            recurring_expense=expense, competence_month=competence_month,
            defaults={"profile_id": profile_id, "amount": expense.amount},
        )
        already = _active_paid(TransactionBatch.objects.filter(
            monthly_expense=monthly, kind="recurring",
        ))
        if already + total > monthly.amount:
            raise ValidationError("Pagamento excede o valor devido nesta competência.")
    elif kind == "unexpected":
        already = _active_paid(TransactionBatch.objects.filter(
            unexpected_expense=expense, kind="unexpected",
        ))
        if already + total > expense.amount:
            raise ValidationError("Pagamento excede a despesa imprevisível.")
    else:
        position = InvestmentPosition.objects.select_for_update().filter(
            pk=investment_id, profile_id=profile_id, is_active=True,
        ).first()
        if position is None:
            raise ValidationError("Investimento inexistente ou inativo neste perfil.")
        if competence_month is not None:
            first = InvestmentPosition.objects.filter(
                profile_id=profile_id, category=position.category, is_active=True,
            ).order_by("pk").first()
            if first.pk != position.pk:
                raise ValidationError("Selecione a posição principal desta categoria para Este mês.")
            from apps.finance.services.monthly import application_due, paid_for_application
            due, monthly_plan = application_due(position, competence_month)
            if due <= ZERO:
                raise ValidationError("Sem aplicação sugerida nesta competência.")
            if monthly_plan is None:
                monthly_plan = MonthlyInvestmentPlan.objects.create(
                    profile_id=profile_id, investment=position,
                    competence_month=competence_month, amount=due,
                )
            if paid_for_application(monthly_plan) + total > monthly_plan.amount:
                raise ValidationError("Aplicação excede o compromisso mensal.")
    accounts = _locked_accounts(profile_id, amounts)
    batch = _create_batch(
        profile_id=profile_id, kind=kind, amount=total,
        occurred_on=occurred_on or timezone.localdate(), competence_month=competence_month,
        note=note[:255], idempotency_key=idempotency_key, created_by=actor,
        recurring_expense_id=recurring_expense_id, monthly_expense=monthly,
        monthly_investment_plan=monthly_plan,
        unexpected_expense_id=unexpected_expense_id, investment=position,
        investment_applied_delta=total if kind == "application" else ZERO,
    )
    _apply_bank_deltas(batch, accounts, {pk: -value for pk, value in amounts.items()})
    postings = [(f"bank:{pk}", ZERO, amount, accounts[pk]) for pk, amount in sorted(amounts.items())]
    contra = f"expense:{kind}" if kind != "application" else f"investment:{investment_id}"
    postings.append((contra, total, ZERO, None))
    _write_journal(batch, postings)
    if position is not None:
        InvestmentPosition.objects.filter(pk=position.pk).update(
            applied_amount=F("applied_amount") + total,
            current_value=F("current_value") + total,
        )
    return batch


@transaction.atomic
def transfer(*, actor, profile_id, source_id, destination_id, amount, idempotency_key,
             occurred_on=None, note=""):
    _key(idempotency_key)
    amount = _amount(amount)
    if source_id == destination_id:
        raise ValidationError("Origem e destino devem ser contas diferentes.")
    require_module(actor, profile_id, "accounts", "view")
    _locked_profile(actor, profile_id)
    expected = (actor.pk, profile_id, "transfer", amount, None, None, None, None,
                {source_id: -amount, destination_id: amount})
    existing = _existing(idempotency_key, expected)
    if existing:
        return existing
    accounts = _locked_accounts(profile_id, {source_id, destination_id})
    batch = _create_batch(
        profile_id=profile_id, kind="transfer", amount=amount,
        occurred_on=occurred_on or timezone.localdate(), note=note[:255],
        idempotency_key=idempotency_key, created_by=actor,
    )
    _apply_bank_deltas(batch, accounts, {source_id: -amount, destination_id: amount})
    _write_journal(batch, [
        (f"bank:{source_id}", ZERO, amount, accounts[source_id]),
        (f"bank:{destination_id}", amount, ZERO, accounts[destination_id]),
    ])
    return batch


@transaction.atomic
def withdraw_investment(*, actor, profile_id, investment_id, destination_id, amount,
                        idempotency_key, occurred_on=None, note=""):
    _key(idempotency_key)
    amount = _amount(amount)
    require_module(actor, profile_id, "investments", "edit")
    require_module(actor, profile_id, "accounts", "view")
    _locked_profile(actor, profile_id)
    expected = (actor.pk, profile_id, "withdrawal", amount, None, None, None, investment_id,
                {destination_id: amount})
    existing = _existing(idempotency_key, expected)
    if existing:
        return existing
    position = InvestmentPosition.objects.select_for_update().filter(
        pk=investment_id, profile_id=profile_id, is_active=True,
    ).first()
    if position is None or position.current_value < amount:
        raise ValidationError("Posição inexistente ou saldo de investimento insuficiente.")
    basis = (position.applied_amount if amount == position.current_value else
             money(position.applied_amount * amount / position.current_value))
    accounts = _locked_accounts(profile_id, {destination_id})
    batch = _create_batch(
        profile_id=profile_id, kind="withdrawal", amount=amount, investment=position,
        investment_applied_delta=-basis, occurred_on=occurred_on or timezone.localdate(),
        note=note[:255], idempotency_key=idempotency_key, created_by=actor,
    )
    _apply_bank_deltas(batch, accounts, {destination_id: amount})
    _write_journal(batch, [
        (f"bank:{destination_id}", amount, ZERO, accounts[destination_id]),
        (f"investment:{investment_id}", ZERO, amount, None),
    ])
    InvestmentPosition.objects.filter(pk=position.pk).update(
        applied_amount=F("applied_amount") - basis,
        current_value=F("current_value") - amount,
    )
    return batch


@transaction.atomic
def reverse_batch(*, actor, profile_id, batch_id, idempotency_key, note=""):
    _key(idempotency_key)
    _locked_profile(actor, profile_id)
    original = TransactionBatch.objects.select_for_update().filter(
        pk=batch_id, profile_id=profile_id,
    ).first()
    if original is None or original.kind == "reversal":
        raise ValidationError("Movimentação original inválida para estorno.")
    if original.kind in {"recurring", "unexpected"}:
        require_module(actor, profile_id, "expenses", "edit")
    if original.kind in {"application", "withdrawal"}:
        require_module(actor, profile_id, "investments", "edit")
    require_module(actor, profile_id, "accounts", "view")
    existing = TransactionBatch.objects.filter(reversal_of=original).first()
    if existing:
        if existing.idempotency_key == idempotency_key and existing.created_by_id == actor.pk:
            return existing
        raise ValidationError("Movimentação já estornada.")
    if TransactionBatch.objects.filter(idempotency_key=idempotency_key).exists():
        raise ValidationError("Chave idempotente já utilizada.")
    position = None
    if original.investment_id:
        position = InvestmentPosition.objects.select_for_update().get(pk=original.investment_id)
        new_current = position.current_value + (
            original.amount if original.kind == "withdrawal" else -original.amount
        )
        new_applied = position.applied_amount - original.investment_applied_delta
        if new_current < ZERO or new_applied < ZERO:
            raise ValidationError("Posição sem saldo suficiente para estornar.")
    legs = list(original.legs.select_related("account").order_by("account_id"))
    deltas = {leg.account_id: -leg.delta for leg in legs}
    accounts = _locked_accounts(profile_id, deltas)
    batch = _create_batch(
        profile_id=profile_id, kind="reversal", amount=original.amount,
        occurred_on=timezone.localdate(), competence_month=original.competence_month,
        note=note[:255], idempotency_key=idempotency_key, created_by=actor,
        recurring_expense=original.recurring_expense, monthly_expense=original.monthly_expense,
        monthly_investment_plan=original.monthly_investment_plan,
        unexpected_expense=original.unexpected_expense, investment=original.investment,
        investment_applied_delta=-original.investment_applied_delta,
        reversal_of=original,
    )
    _apply_bank_deltas(batch, accounts, deltas)
    _write_journal(batch, [
        (entry.account_code, entry.credit, entry.debit, entry.bank_account)
        for entry in original.journal_entries.all()
    ])
    if position is not None:
        InvestmentPosition.objects.filter(pk=position.pk).update(
            applied_amount=new_applied, current_value=new_current,
        )
    return batch


def reconcile_account(account):
    """Read-only result: None for legacy or unknown opening balances."""
    if account.opening_balance is None or account.balance is None:
        return None
    delta = account.ledgerleg_set.aggregate(total=Sum("delta"))["total"] or ZERO
    return money(account.opening_balance + delta) == account.balance


@transaction.atomic
def reverse_item_payments(*, actor, profile_id, kind, object_id, competence_month,
                          idempotency_key):
    """Uncheck one monthly item, reversing every active partial payment atomically."""
    _key(idempotency_key)
    if kind not in {"recurring", "unexpected", "application"}:
        raise ValidationError("Tipo de item inválido para desmarcar.")
    require_module(actor, profile_id, "investments" if kind == "application" else "expenses", "edit")
    _locked_profile(actor, profile_id)
    filters = {"kind": kind, "profile_id": profile_id, "reversal__isnull": True}
    if kind == "recurring":
        filters.update(recurring_expense_id=object_id, competence_month=competence_month)
    elif kind == "unexpected":
        filters.update(unexpected_expense_id=object_id)
    else:
        filters.update(investment_id=object_id, competence_month=competence_month,
                       monthly_investment_plan__isnull=False)
    originals = list(TransactionBatch.objects.filter(**filters).order_by("pk"))
    if not originals:
        raise ValidationError("Nenhum pagamento ativo para estornar.")
    return [
        reverse_batch(
            actor=actor, profile_id=profile_id, batch_id=original.pk,
            idempotency_key=f"{idempotency_key[:90]}:{original.pk}",
        )
        for original in originals
    ]
