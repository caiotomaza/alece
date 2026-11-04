# SPDX-License-Identifier: GPL-3.0-only
"""Editar Principal no formulário administrativo e na rota compatível."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.finance.models import FinancialProfile, Workspace, WorkspaceMembership


class PrincipalProfileEditTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username="principal-admin", password="Example123!")
        self.workspace = Workspace.objects.create(name="Casa", created_by=self.admin)
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.admin, role="admin")
        self.principal = FinancialProfile.objects.create(workspace=self.workspace, name="Principal")
        self.client.force_login(self.admin)

    def test_modal_has_explicit_post_target(self):
        url = reverse("finance:profile-manage", args=[self.principal.pk])
        response = self.client.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'action="{url}"')

    def test_edit_principal_name_emoji_income(self):
        url = reverse("finance:profile-manage", args=[self.principal.pk])
        response = self.client.post(url, {
            "action": "profile", "name": "Pessoal", "emoji": "💼", "monthly_income": "4250.35",
        }, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 302)
        self.principal.refresh_from_db()
        self.assertEqual(self.principal.name, "Pessoal")
        self.assertEqual(self.principal.emoji, "💼")
        self.assertEqual(self.principal.monthly_income, Decimal("4250.35"))

    def test_edit_legacy_url_does_not_archive_profile(self):
        url = reverse("finance:profile-edit", args=[self.principal.pk])
        response = self.client.post(url, {
            "name": "Principal Atualizado", "emoji": "", "monthly_income": "0",
        })
        self.assertEqual(response.status_code, 302)
        self.principal.refresh_from_db()
        self.assertFalse(self.principal.is_archived)
        self.assertEqual(self.principal.monthly_income, Decimal("0"))

    def test_archived_principal_can_change_metadata_without_reactivation(self):
        FinancialProfile.objects.create(workspace=self.workspace, name="Reserva")
        self.principal.is_archived = True
        self.principal.save(update_fields=["is_archived"])
        url = reverse("finance:profile-manage", args=[self.principal.pk])
        response = self.client.post(url, {"action":"profile", "name":"Arquivo", "emoji":""})
        self.assertEqual(response.status_code, 302)
        self.principal.refresh_from_db()
        self.assertTrue(self.principal.is_archived)
        self.assertEqual(self.principal.name, "Arquivo")
