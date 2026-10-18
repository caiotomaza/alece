# SPDX-License-Identifier: GPL-3.0-only
from django import forms

from apps.finance.models import (
    BankAccount, FinancialProfile, InvestmentPosition, RecurringExpense, ReservePolicy,
    UnexpectedExpense,
)


class FinancialProfileForm(forms.ModelForm):
    monthly_income = forms.DecimalField(
        label="Renda mensal", required=False, min_value=0, max_digits=15, decimal_places=2,
        help_text="Deixe em branco se desconhecida. Zero significa renda informada como zero.",
    )

    class Meta:
        model = FinancialProfile
        fields = ["name", "emoji", "monthly_income", "is_archived"]
        labels = {"name": "Nome", "emoji": "Emoji", "is_archived": "Arquivado"}


class BankAccountForm(forms.ModelForm):
    balance = forms.DecimalField(
        label="Saldo informado", required=False, min_value=0, max_digits=15, decimal_places=2,
        help_text="Deixe em branco se desconhecido. Zero significa saldo informado como zero.",
    )

    class Meta:
        model = BankAccount
        fields = ["name", "kind", "balance", "is_archived"]
        labels = {"name": "Nome", "kind": "Tipo", "is_archived": "Arquivada"}


class RecurringExpenseForm(forms.ModelForm):
    class Meta:
        model = RecurringExpense
        fields = ["name", "category", "amount", "due_day", "is_active"]
        labels = {"name": "Nome", "category": "Categoria", "amount": "Valor mensal", "due_day": "Dia do vencimento", "is_active": "Ativa"}
        help_texts = {"due_day": "De 1 a 31. Em meses mais curtos, vence no último dia válido."}


class UnexpectedExpenseForm(forms.ModelForm):
    class Meta:
        model = UnexpectedExpense
        fields = ["name", "amount"]
        labels = {"name": "Nome", "amount": "Valor"}


class InvestmentPositionForm(forms.ModelForm):
    class Meta:
        model = InvestmentPosition
        fields = ["name", "institution", "category", "applied_amount", "current_value", "recorded_on", "target_amount", "is_active"]
        labels = {"name": "Nome", "institution": "Instituição", "category": "Categoria", "applied_amount": "Valor aplicado", "current_value": "Valor líquido atual", "recorded_on": "Data da posição", "target_amount": "Meta opcional", "is_active": "Ativo"}
        widgets = {"recorded_on": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})}
        help_texts = {"target_amount": "Somente para as três categorias de objetivos. A meta da Reserva é automática."}


class ReservePolicyForm(forms.ModelForm):
    class Meta:
        model = ReservePolicy
        fields = ["coverage_months"]
        labels = {"coverage_months": "Meses de proteção"}
        help_texts = {"coverage_months": "De 6 a 12 meses de despesas essenciais. Padrão: 9 meses."}
