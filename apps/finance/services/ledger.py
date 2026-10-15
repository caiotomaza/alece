# SPDX-License-Identifier: GPL-3.0-only
"""Operações com caixa dentro de transação, sem signals e sem saldo negativo.

A mesma chave idempotente evita confirmação duplicada em requests concorrentes.
API de estorno e reconciliação fica como trabalho pendente, NÃO implementada aqui.
"""
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F

from apps.finance.domain.calculations import money
from apps.finance.models import BankAccount, FinancialProfile, LedgerLeg, TransactionBatch


@transaction.atomic
def confirm_outflow(
    *,
    profile_id: int,
    kind: str,
    splits: dict[int, Decimal],
    idempotency_key: str,
    note: str = "",
    occurred_on: date | None = None,
    recurring_expense_id: int | None = None,
    unexpected_expense_id: int | None = None,
    investment_id: int | None = None,
):
    allowed = {
        TransactionBatch.Kind.RECURRING,
        TransactionBatch.Kind.UNEXPECTED,
        TransactionBatch.Kind.APPLICATION,
    }
    if kind not in allowed:
        raise ValidationError("Tipo inválido para saída de caixa.")
    if not idempotency_key or len(idempotency_key) > 120:
        raise ValidationError("Chave idempotente obrigatória.")
    if not splits:
        raise ValidationError("Informe ao menos uma conta de origem.")
    FinancialProfile.objects.get(pk=profile_id)
    amounts = {int(pk): money(value) for pk, value in splits.items()}
    if any(amt <= 0 for amt in amounts.values()):
        raise ValidationError("Todas as parcelas devem ser positivas.")
    total = sum(amounts.values(), Decimal("0.00"))
    existing = TransactionBatch.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        recorded = {leg.account_id: -leg.delta for leg in existing.legs.all()}
        if (existing.profile_id != profile_id or existing.kind != kind
                or existing.amount != total or recorded != amounts):
            raise ValidationError("Chave idempotente reaproveitada com dados divergentes.")
        return existing
    accounts = list(BankAccount.objects.select_for_update().filter(pk__in=sorted(amounts)))
    if len(accounts) != len(amounts):
        raise ValidationError("Conta inexistente.")
    for account in accounts:
        amount = amounts[account.pk]
        if account.profile_id != profile_id:
            raise ValidationError("Conta pertence a outro perfil financeiro.")
        if account.balance is None or account.balance < amount:
            raise ValidationError(f"Saldo insuficiente ou desconhecido: {account.name}.")
        if account.is_archived:
            raise ValidationError(f"Conta arquivada: {account.name}.")
    # Vínculos precisam pertencer ao mesmo perfil; validação explícita antes do commit.
    from apps.finance.models import InvestmentPosition, RecurringExpense, UnexpectedExpense
    if recurring_expense_id and not RecurringExpense.objects.filter(pk=recurring_expense_id, profile_id=profile_id).exists():
        raise ValidationError("Despesa previsível de outro perfil.")
    if unexpected_expense_id and not UnexpectedExpense.objects.filter(pk=unexpected_expense_id, profile_id=profile_id).exists():
        raise ValidationError("Despesa imprevisível de outro perfil.")
    if kind == TransactionBatch.Kind.APPLICATION and not investment_id:
        raise ValidationError("Aplicação exige posição de investimento existente.")
    position = None
    if investment_id:
        position = InvestmentPosition.objects.select_for_update().filter(
            pk=investment_id, profile_id=profile_id
        ).first()
        if position is None:
            raise ValidationError("Investimento de outro perfil.")
    try:
        batch = TransactionBatch.objects.create(
            profile_id=profile_id, kind=kind, amount=total, note=note[:255],
            idempotency_key=idempotency_key, occurred_on=occurred_on or date.today(),
            recurring_expense_id=recurring_expense_id,
            unexpected_expense_id=unexpected_expense_id,
            investment_id=investment_id,
        )
    except IntegrityError:
        # Em corrida de mesma chave, não executar débito duas vezes.
        raise ValidationError("Operação já confirmada concorrentemente; consulte o histórico.")
    for account in accounts:
        delta = -amounts[account.pk]
        BankAccount.objects.filter(pk=account.pk).update(balance=F("balance") + delta)
        LedgerLeg.objects.create(batch=batch, account=account, delta=delta)
    if kind == TransactionBatch.Kind.APPLICATION:
        InvestmentPosition.objects.filter(pk=position.pk).update(
            applied_amount=F("applied_amount") + total,
            current_value=F("current_value") + total,
        )
    return batch
