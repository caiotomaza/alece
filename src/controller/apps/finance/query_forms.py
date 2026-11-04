# SPDX-License-Identifier: GPL-3.0-only
from django import forms
from django.utils import timezone

from apps.finance.forms import FinancialProfileForm


class WorkspaceFilterForm(forms.Form):
    profiles = forms.ModelMultipleChoiceField(
        queryset=None, required=False, label="Perfis financeiros",
        help_text="Sem seleção: todos os perfis ativos aos quais você tem acesso.",
        widget=forms.CheckboxSelectMultiple,
    )
    month = forms.DateField(
        required=False, label="Mês", input_formats=["%Y-%m"],
        widget=forms.DateInput(format="%Y-%m", attrs={"type": "month"}),
    )

    def __init__(self, *args, profiles, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["profiles"].queryset = profiles

    def clean_month(self):
        value = self.cleaned_data.get("month") or timezone.localdate()
        return value.replace(day=1)


class IncomeForm(forms.Form):
    monthly_income = FinancialProfileForm.base_fields["monthly_income"]
