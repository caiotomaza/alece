# SPDX-License-Identifier: GPL-3.0-only
from decimal import Decimal

from django import forms
from django.utils.formats import localize

from apps.finance.models import BankAccount


class BalanceCheckboxes(forms.CheckboxSelectMultiple):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value and hasattr(value, "instance"):
            option["attrs"]["data-balance"] = str(value.instance.balance)
        return option


class AccountChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name} — R$ {localize(obj.balance)}"


class PaymentForm(forms.Form):
    amount = forms.DecimalField(label="Valor a confirmar", min_value=Decimal("0.01"), max_digits=15, decimal_places=2)
    accounts = AccountChoiceField(
        queryset=BankAccount.objects.none(), label="Contas de origem",
        widget=BalanceCheckboxes,
    )
    idempotency_key = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, profile, remaining, **kwargs):
        super().__init__(*args, **kwargs)
        self.remaining = remaining
        self.fields["amount"].initial = remaining
        self.fields["accounts"].queryset = profile.accounts.filter(
            is_archived=False, balance__gt=0, opening_balance__isnull=False,
        ).order_by("pk")

    def clean_amount(self):
        value = self.cleaned_data["amount"]
        if self.remaining is not None and value > self.remaining:
            raise forms.ValidationError("Valor superior ao saldo pendente deste item.")
        return value


class TransferForm(forms.Form):
    source = forms.ModelChoiceField(queryset=BankAccount.objects.none(), label="Origem")
    destination = forms.ModelChoiceField(queryset=BankAccount.objects.none(), label="Destino")
    amount = forms.DecimalField(label="Valor", min_value=Decimal("0.01"), max_digits=15, decimal_places=2)
    note = forms.CharField(label="Descrição", max_length=255, required=False)
    idempotency_key = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, profile, **kwargs):
        super().__init__(*args, **kwargs)
        accounts = profile.accounts.filter(
            is_archived=False, balance__isnull=False, opening_balance__isnull=False,
        ).order_by("pk")
        self.fields["source"].queryset = accounts.filter(balance__gt=0)
        self.fields["destination"].queryset = accounts


class WithdrawalForm(forms.Form):
    destination = forms.ModelChoiceField(queryset=BankAccount.objects.none(), label="Conta de destino")
    amount = forms.DecimalField(label="Valor a resgatar", min_value=Decimal("0.01"), max_digits=15, decimal_places=2)
    idempotency_key = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, profile, position, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["amount"].max_value = position.current_value
        self.fields["amount"].initial = position.current_value
        self.fields["destination"].queryset = profile.accounts.filter(
            is_archived=False, balance__isnull=False, opening_balance__isnull=False,
        ).order_by("pk")
