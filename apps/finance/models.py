# SPDX-License-Identifier: GPL-3.0-only
"""Entidades estruturais. Não executar débitos por signals nem sobrescrita de save()."""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


class Workspace(models.Model):
    name = models.CharField(max_length=100)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class WorkspaceMembership(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrador"
        COMMON = "common", "Comum"

    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=8, choices=Role.choices, default=Role.COMMON)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["workspace", "user"], name="uq_member_user")]


class FinancialProfile(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="profiles")
    name = models.CharField(max_length=80)
    emoji = models.CharField(max_length=16, blank=True)
    monthly_income = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["workspace", "name"], name="uq_profile_workspace_name"),
            models.CheckConstraint(condition=Q(monthly_income__gte=0) | Q(monthly_income__isnull=True), name="ck_monthly_income_nonnegative"),
        ]

    def __str__(self):
        return self.name


class ProfileGrant(models.Model):
    membership = models.ForeignKey(WorkspaceMembership, on_delete=models.CASCADE)
    profile = models.ForeignKey(FinancialProfile, on_delete=models.CASCADE)
    can_view = models.BooleanField(default=True)
    can_edit = models.BooleanField(default=False)

    def clean(self):
        if self.membership_id and self.profile_id:
            if self.membership.workspace_id != self.profile.workspace_id:
                raise ValidationError("Concessão deve pertencer ao mesmo núcleo do perfil.")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["membership", "profile"], name="uq_member_profile_grant")]


class BankAccount(models.Model):
    class Kind(models.TextChoices):
        BANK = "bank", "Conta bancária"
        CASH = "cash", "Dinheiro físico"

    profile = models.ForeignKey(FinancialProfile, on_delete=models.PROTECT, related_name="accounts")
    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.BANK)
    balance = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["profile", "name"], name="uq_account_profile_name"),
            models.CheckConstraint(condition=Q(balance__gte=0) | Q(balance__isnull=True), name="ck_account_nonnegative"),
        ]

    def __str__(self):
        return f"{self.profile} / {self.name}"


class RecurringExpense(models.Model):
    class Category(models.TextChoices):
        ESSENTIAL = "essential", "Essenciais"
        STRATEGIC = "strategic", "Estratégicas"
        DISCRETIONARY = "discretionary", "Discricionárias"

    profile = models.ForeignKey(FinancialProfile, on_delete=models.PROTECT)
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=14, choices=Category.choices)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    due_day = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(31)])
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="ck_recurring_amount_positive"),
            models.CheckConstraint(condition=Q(due_day__gte=1, due_day__lte=31), name="ck_recurring_due_day_range"),
        ]

    def __str__(self):
        return self.name


class UnexpectedExpense(models.Model):
    profile = models.ForeignKey(FinancialProfile, on_delete=models.PROTECT)
    name = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    recorded_on = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="ck_unexpected_amount_positive")]


class InvestmentPosition(models.Model):
    class Category(models.TextChoices):
        DEVELOPMENT = "development", "Desenvolvimento pessoal e profissional"
        PATRIMONY = "patrimony", "Aquisição patrimonial"
        PLANNED = "planned", "Consumo planejado"
        RESERVE = "reserve", "Reserva"

    profile = models.ForeignKey(FinancialProfile, on_delete=models.PROTECT)
    name = models.CharField(max_length=160)
    institution = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=12, choices=Category.choices)
    applied_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    current_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    target_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    recorded_on = models.DateField(null=True, blank=True)

    def clean(self):
        if self.category == self.Category.RESERVE and self.target_amount is not None:
            raise ValidationError({"target_amount": "A meta da Reserva é calculada automaticamente."})

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(applied_amount__gte=0), name="ck_applied_amount_nonnegative"),
            models.CheckConstraint(condition=Q(current_value__gte=0), name="ck_current_value_nonnegative"),
            models.CheckConstraint(condition=Q(target_amount__gt=0) | Q(target_amount__isnull=True), name="ck_target_positive_or_null"),
            models.CheckConstraint(condition=~Q(category="reserve") | Q(target_amount__isnull=True), name="ck_reserve_no_manual_target"),
        ]


class ReservePolicy(models.Model):
    profile = models.OneToOneField(FinancialProfile, on_delete=models.CASCADE)
    coverage_months = models.PositiveSmallIntegerField(default=9, validators=[MinValueValidator(6), MaxValueValidator(12)])

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(coverage_months__gte=6, coverage_months__lte=12), name="ck_reserve_months_range")]


class TransactionBatch(models.Model):
    class Kind(models.TextChoices):
        RECURRING = "recurring", "Pagamento previsível"
        UNEXPECTED = "unexpected", "Despesa imprevisível"
        APPLICATION = "application", "Aplicação"
        WITHDRAWAL = "withdrawal", "Resgate"
        TRANSFER = "transfer", "Transferência"
        INCOME = "income", "Recebimento"
        REVERSAL = "reversal", "Estorno"

    profile = models.ForeignKey(FinancialProfile, on_delete=models.PROTECT)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    occurred_on = models.DateField()
    note = models.CharField(max_length=255, blank=True)
    idempotency_key = models.CharField(max_length=120, unique=True, null=True, blank=True)
    recurring_expense = models.ForeignKey(RecurringExpense, on_delete=models.PROTECT, null=True, blank=True)
    unexpected_expense = models.ForeignKey(UnexpectedExpense, on_delete=models.PROTECT, null=True, blank=True)
    investment = models.ForeignKey(InvestmentPosition, on_delete=models.PROTECT, null=True, blank=True)
    reversal_of = models.OneToOneField("self", on_delete=models.PROTECT, null=True, blank=True, related_name="reversal")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="ck_transaction_amount_positive")]


class LedgerLeg(models.Model):
    batch = models.ForeignKey(TransactionBatch, on_delete=models.PROTECT, related_name="legs")
    account = models.ForeignKey(BankAccount, on_delete=models.PROTECT)
    delta = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        constraints = [models.CheckConstraint(condition=~Q(delta=0), name="ck_leg_nonzero")]
