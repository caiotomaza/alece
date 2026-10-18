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
    class Level(models.TextChoices):
        NONE = "none", "Sem acesso"
        VIEW = "view", "Visualizar"
        EDIT = "edit", "Editar"

    membership = models.ForeignKey(WorkspaceMembership, on_delete=models.CASCADE)
    profile = models.ForeignKey(FinancialProfile, on_delete=models.CASCADE)
    can_view = models.BooleanField(default=True)
    can_edit = models.BooleanField(default=False)
    overview_level = models.CharField(max_length=4, choices=Level.choices, default=Level.NONE)
    accounts_level = models.CharField(max_length=4, choices=Level.choices, default=Level.NONE)
    expenses_level = models.CharField(max_length=4, choices=Level.choices, default=Level.NONE)
    investments_level = models.CharField(max_length=4, choices=Level.choices, default=Level.NONE)
    movements_level = models.CharField(max_length=4, choices=Level.choices, default=Level.NONE)

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
    # NULL on legacy rows deliberately means that their opening balance has not been reconciled.
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
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
    competence_month = models.DateField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True)
    investment_applied_delta = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    idempotency_key = models.CharField(max_length=120, unique=True, null=True, blank=True)
    recurring_expense = models.ForeignKey(RecurringExpense, on_delete=models.PROTECT, null=True, blank=True)
    monthly_expense = models.ForeignKey("MonthlyExpense", on_delete=models.PROTECT, null=True, blank=True)
    monthly_investment_plan = models.ForeignKey(
        "MonthlyInvestmentPlan", on_delete=models.PROTECT, null=True, blank=True,
    )
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


class MonthlyExpense(models.Model):
    """Frozen amount for one recurring expense and competence month."""

    profile = models.ForeignKey(FinancialProfile, on_delete=models.PROTECT)
    recurring_expense = models.ForeignKey(RecurringExpense, on_delete=models.PROTECT)
    competence_month = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["recurring_expense", "competence_month"], name="uq_monthly_expense"),
            models.CheckConstraint(condition=Q(amount__gt=0), name="ck_monthly_expense_positive"),
        ]


class MonthlyInvestmentPlan(models.Model):
    """Monthly suggestion frozen on first confirmed application."""

    profile = models.ForeignKey(FinancialProfile, on_delete=models.PROTECT)
    investment = models.ForeignKey(InvestmentPosition, on_delete=models.PROTECT)
    competence_month = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["investment", "competence_month"], name="uq_monthly_investment_plan"),
            models.CheckConstraint(condition=Q(amount__gt=0), name="ck_monthly_investment_positive"),
        ]


class JournalEntry(models.Model):
    """One side of an immutable double-entry batch; debits equal credits per batch."""

    batch = models.ForeignKey(TransactionBatch, on_delete=models.PROTECT, related_name="journal_entries")
    account_code = models.CharField(max_length=80)
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    bank_account = models.ForeignKey(BankAccount, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(
            condition=(Q(debit__gt=0, credit=0) | Q(credit__gt=0, debit=0)),
            name="ck_journal_one_positive_side",
        )]


class ImportBatch(models.Model):
    """Staging batch for bank statement imports (CSV/OFX)."""
    class Format(models.TextChoices):
        CSV = "csv", "CSV"
        OFX = "ofx", "OFX"
        OFX2 = "ofx2", "OFX 2.x (XML)"

    class Status(models.TextChoices):
        STAGED = "staged", "Em staging"
        VALIDATED = "validated", "Validado"
        REVIEWED = "reviewed", "Revisado"
        COMMITTED = "committed", "Confirmado"
        FAILED = "failed", "Falhou"

    profile = models.ForeignKey(FinancialProfile, on_delete=models.PROTECT, related_name="import_batches")
    account = models.ForeignKey(BankAccount, on_delete=models.PROTECT, related_name="import_batches", null=True, blank=True)
    filename = models.CharField(max_length=255)
    file_hash = models.CharField(max_length=64)  # SHA-256
    format = models.CharField(max_length=8, choices=Format.choices)
    parser_version = models.CharField(max_length=32)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.STAGED)
    total_rows = models.PositiveIntegerField(default=0)
    valid_rows = models.PositiveIntegerField(default=0)
    duplicate_rows = models.PositiveIntegerField(default=0)
    error_rows = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    committed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class ImportRow(models.Model):
    """Individual row from an import batch, awaiting review and commit."""
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        SUGGESTED = "suggested", "Sugerido"
        DUPLICATE = "duplicate", "Duplicado"
        IGNORED = "ignored", "Ignorado"
        COMMITTED = "committed", "Confirmado"
        ERROR = "error", "Erro"

    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE, related_name="rows")
    row_number = models.PositiveIntegerField()
    fitid = models.CharField(max_length=120, blank=True)  # OFX unique transaction ID
    occurred_on = models.DateField()
    posted_on = models.DateField(null=True, blank=True)  # Data de compensação (opcional)
    description = models.CharField(max_length=255)
    memo = models.TextField(blank=True)  # Memo/detalhes adicionais
    amount = models.DecimalField(max_digits=15, decimal_places=2)  # Valor com sinal
    is_credit = models.BooleanField(default=False)  # True = crédito, False = débito
    raw_data = models.JSONField(default=dict)  # Dados originais normalizados
    suggested_kind = models.CharField(max_length=12, blank=True)  # recurring, unexpected, application, withdrawal, transfer, income, reversal
    suggested_link = models.JSONField(default=dict)  # Vínculo sugerido (expense_id, investment_id, etc.)
    confidence = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0.00"))  # 0.00 a 1.00
    justification = models.TextField(blank=True)  # Justificativa da sugestão
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    linked_batch = models.ForeignKey(TransactionBatch, on_delete=models.PROTECT, null=True, blank=True, related_name="import_rows")
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["batch", "row_number"]
        constraints = [
            models.UniqueConstraint(fields=["batch", "row_number"], name="uq_import_row_number"),
        ]
