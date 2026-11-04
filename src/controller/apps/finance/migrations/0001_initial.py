# SPDX-License-Identifier: GPL-3.0-only
# Generated as bootstrap schema; validate via makemigrations --check in CI.
import decimal

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="Workspace",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="WorkspaceMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("admin", "Administrador"), ("common", "Comum")], default="common", max_length=8)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="finance.workspace")),
            ],
            options={"constraints": [models.UniqueConstraint(fields=("workspace", "user"), name="uq_member_user")]},
        ),
        migrations.CreateModel(
            name="FinancialProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80)),
                ("emoji", models.CharField(blank=True, max_length=16)),
                ("monthly_income", models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="profiles", to="finance.workspace")),
            ],
            options={"constraints": [
                models.UniqueConstraint(fields=("workspace", "name"), name="uq_profile_workspace_name"),
                models.CheckConstraint(condition=Q(monthly_income__gte=0) | Q(monthly_income__isnull=True), name="ck_monthly_income_nonnegative"),
            ]},
        ),
        migrations.CreateModel(
            name="ProfileGrant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("can_view", models.BooleanField(default=True)),
                ("can_edit", models.BooleanField(default=False)),
                ("membership", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="finance.workspacemembership")),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="finance.financialprofile")),
            ],
            options={"constraints": [models.UniqueConstraint(fields=("membership", "profile"), name="uq_member_profile_grant")]},
        ),
        migrations.CreateModel(
            name="BankAccount",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("kind", models.CharField(choices=[("bank", "Conta bancária"), ("cash", "Dinheiro físico")], default="bank", max_length=8)),
                ("balance", models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ("is_archived", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="accounts", to="finance.financialprofile")),
            ],
            options={"constraints": [
                models.UniqueConstraint(fields=("profile", "name"), name="uq_account_profile_name"),
                models.CheckConstraint(condition=Q(balance__gte=0) | Q(balance__isnull=True), name="ck_account_nonnegative"),
            ]},
        ),
        migrations.CreateModel(
            name="RecurringExpense",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("category", models.CharField(choices=[("essential", "Essenciais"), ("strategic", "Estratégicas"), ("discretionary", "Discricionárias")], max_length=14)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=15)),
                ("due_day", models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(31)])),
                ("is_active", models.BooleanField(default=True)),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="finance.financialprofile")),
            ],
            options={"constraints": [models.CheckConstraint(condition=Q(amount__gt=0), name="ck_recurring_amount_positive")]},
        ),
        migrations.CreateModel(
            name="UnexpectedExpense",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=15)),
                ("recorded_on", models.DateField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="finance.financialprofile")),
            ],
            options={"constraints": [models.CheckConstraint(condition=Q(amount__gt=0), name="ck_unexpected_amount_positive")]},
        ),
        migrations.CreateModel(
            name="InvestmentPosition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=160)),
                ("institution", models.CharField(blank=True, max_length=100)),
                ("category", models.CharField(choices=[("development", "Desenvolvimento pessoal e profissional"), ("patrimony", "Aquisição patrimonial"), ("planned", "Consumo planejado"), ("reserve", "Reserva")], max_length=12)),
                ("applied_amount", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=15)),
                ("current_value", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=15)),
                ("target_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="finance.financialprofile")),
            ],
            options={"constraints": [
                models.CheckConstraint(condition=Q(applied_amount__gte=0), name="ck_applied_amount_nonnegative"),
                models.CheckConstraint(condition=Q(current_value__gte=0), name="ck_current_value_nonnegative"),
                models.CheckConstraint(condition=Q(target_amount__gt=0) | Q(target_amount__isnull=True), name="ck_target_positive_or_null"),
            ]},
        ),
        migrations.CreateModel(
            name="ReservePolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("coverage_months", models.PositiveSmallIntegerField(default=9, validators=[django.core.validators.MinValueValidator(6), django.core.validators.MaxValueValidator(12)])),
                ("profile", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to="finance.financialprofile")),
            ],
            options={"constraints": [models.CheckConstraint(condition=Q(coverage_months__gte=6, coverage_months__lte=12), name="ck_reserve_months_range")]},
        ),
        migrations.CreateModel(
            name="TransactionBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("recurring", "Pagamento previsível"), ("unexpected", "Despesa imprevisível"), ("application", "Aplicação"), ("withdrawal", "Resgate"), ("transfer", "Transferência"), ("income", "Recebimento"), ("reversal", "Estorno")], max_length=12)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=15)),
                ("occurred_on", models.DateField()),
                ("note", models.CharField(blank=True, max_length=255)),
                ("idempotency_key", models.CharField(blank=True, max_length=120, null=True, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("investment", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="finance.investmentposition")),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="finance.financialprofile")),
                ("recurring_expense", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="finance.recurringexpense")),
                ("reversal_of", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="reversal", to="finance.transactionbatch")),
                ("unexpected_expense", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="finance.unexpectedexpense")),
            ],
            options={"constraints": [models.CheckConstraint(condition=Q(amount__gt=0), name="ck_transaction_amount_positive")]},
        ),
        migrations.CreateModel(
            name="LedgerLeg",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("delta", models.DecimalField(decimal_places=2, max_digits=15)),
                ("account", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="finance.bankaccount")),
                ("batch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="legs", to="finance.transactionbatch")),
            ],
            options={"constraints": [models.CheckConstraint(condition=~Q(delta=0), name="ck_leg_nonzero")]},
        ),
    ]
