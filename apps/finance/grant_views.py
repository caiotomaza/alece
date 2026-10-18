# SPDX-License-Identifier: GPL-3.0-only
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.core.permissions import require_workspace_admin
from apps.finance.forms import ProfileGrantForm
from apps.finance.models import FinancialProfile, ProfileGrant, WorkspaceMembership
from apps.finance.services.grants import GRANT_FIELDS, save_grant


@login_required
@require_http_methods(["GET"])
def grant_list(request, profile_id):
    profile = get_object_or_404(FinancialProfile, pk=profile_id)
    require_workspace_admin(request.user, profile.workspace_id)
    members = WorkspaceMembership.objects.filter(
        workspace_id=profile.workspace_id, role=WorkspaceMembership.Role.COMMON,
    ).select_related("user").order_by("user__username")
    grants = {
        grant.membership_id: grant for grant in ProfileGrant.objects.filter(profile=profile)
    }
    rows = [{"member": member, "grant": grants.get(member.pk)} for member in members]
    return render(request, "finance/grant_list.html", {
        "profile": profile, "workspace": profile.workspace, "rows": rows,
    })


@login_required
@require_http_methods(["GET", "POST"])
def grant_edit(request, profile_id, membership_id):
    profile = get_object_or_404(FinancialProfile, pk=profile_id)
    require_workspace_admin(request.user, profile.workspace_id)
    member = get_object_or_404(
        WorkspaceMembership, pk=membership_id, workspace_id=profile.workspace_id,
        role=WorkspaceMembership.Role.COMMON,
    )
    grant = ProfileGrant.objects.filter(profile=profile, membership=member).first()
    form = ProfileGrantForm(request.POST if request.method == "POST" else None, instance=grant)
    if request.method == "POST" and form.is_valid():
        try:
            save_grant(
                actor=request.user, profile_id=profile.pk, membership_id=member.pk,
                levels={field: form.cleaned_data[field] for field in GRANT_FIELDS},
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            messages.success(request, "Permissões atualizadas; valem na próxima requisição.")
            return redirect("finance:grant-list", profile_id=profile.pk)
    return render(request, "finance/object_form.html", {
        "workspace": profile.workspace, "profile": profile, "form": form,
        "title": f"Permissões de {member.user.username} · {profile.name}",
        "cancel_url": reverse("finance:grant-list", args=[profile.pk]),
    })
