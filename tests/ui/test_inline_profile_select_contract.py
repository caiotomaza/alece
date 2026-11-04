# SPDX-License-Identifier: GPL-3.0-only
"""Contrato estático: cadastro abre o formulário direto e usa seletor autorizado."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_no_separate_picker_template_or_references():
    assert not (ROOT / "src/view/templates/finance/choose_profile.html").exists()
    view = (ROOT / "src/controller/apps/finance/views.py").read_text()
    assert 'render(request, "finance/choose_profile.html"' not in view
    assert 'return render(request, "finance/object_form.html"' in view
    assert '"profile_id": forms.ModelChoiceField(' in view
    assert 'save_record(request.user, profile.pk, model, form.cleaned_data)' in view


def test_financial_profile_dropdown_is_inside_form_with_csrf():
    template = (ROOT / "src/view/templates/finance/object_form.html").read_text()
    assert '<form method="post" class="object-form">' in template
    assert '{% csrf_token %}' in template
    assert '{% for field in form %}' in template
    assert '{{ field.label_tag }} {{ field }}' in template
    assert 'dialog-profile-value' in template  # edits remain tied to fixed records


def test_transfer_profile_selector_reloads_account_choices_without_second_modal():
    view = (ROOT / "src/controller/apps/finance/transaction_views.py").read_text()
    js = (ROOT / "src/view/static/finance/alece.js").read_text()
    assert '"data-profile-refresh": "true"' in view
    assert 'request.POST.get("profile_id")' in view
    assert 'require_module(request.user, profile.pk, "movements", "edit")' in view
    assert 'document.addEventListener(\'change\', async (event)' in js
    assert "modal.replaceChildren(replacement)" in js
