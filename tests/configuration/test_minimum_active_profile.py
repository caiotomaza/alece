# SPDX-License-Identifier: GPL-3.0-only
"""Invariante: pelo menos um perfil ativo; Principal é editável como qualquer outro."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.finance.models import FinancialProfile, Workspace, WorkspaceMembership
from apps.finance.services.profiles import delete_financial_profile, update_financial_profile


class MinimumActiveFinancialProfileTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="active_profile_owner", password="Example123!"
        )
        self.workspace = Workspace.objects.create(name="Finanças", created_by=self.owner)
        WorkspaceMembership.objects.create(
            workspace=self.workspace, user=self.owner, role=WorkspaceMembership.Role.ADMIN,
        )
        self.principal = FinancialProfile.objects.create(
            workspace=self.workspace, name="Principal", monthly_income=Decimal("2300.00"),
        )
        self.client.force_login(self.owner)
        self.url = reverse("finance:profile-manage", args=[self.principal.pk])

    def test_principal_single_profile_can_edit_name_emoji_and_income(self):
        response = self.client.post(self.url, {
            "action": "profile", "name": "Casa", "emoji": "🏠", "monthly_income": "3150.00",
        })
        self.assertRedirects(response, reverse("configuracoes-perfis"))
        self.principal.refresh_from_db()
        self.assertEqual(self.principal.name, "Casa")
        self.assertEqual(self.principal.emoji, "🏠")
        self.assertEqual(self.principal.monthly_income, Decimal("3150.00"))
        self.assertFalse(self.principal.is_archived)

    def test_single_active_cannot_delete_direct_service(self):
        with self.assertRaisesMessage(ValidationError, "ao menos um perfil ativo"):
            delete_financial_profile(self.owner, self.principal.pk, "CONFIRMAR")
        self.principal.refresh_from_db()
        self.assertIsNone(self.principal.deleted_at)
        self.assertFalse(self.principal.is_archived)

    def test_single_active_cannot_archive_direct_service(self):
        with self.assertRaisesMessage(ValidationError, "ao menos um perfil ativo"):
            update_financial_profile(self.owner, self.principal.pk, {"is_archived": True})
        self.principal.refresh_from_db()
        self.assertFalse(self.principal.is_archived)

    def test_single_active_cannot_delete_via_post(self):
        response = self.client.post(self.url, {
            "action": "delete_profile", "confirm_deletion": "CONFIRMAR",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ao menos um perfil ativo")
        self.principal.refresh_from_db()
        self.assertIsNone(self.principal.deleted_at)

    def test_single_active_cannot_archive_via_post(self):
        response = self.client.post(self.url, {"action": "toggle_archive"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ao menos um perfil ativo")
        self.principal.refresh_from_db()
        self.assertFalse(self.principal.is_archived)

    def test_interface_blocks_destructive_actions_but_keeps_profile_edit(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "último perfil ativo")
        self.assertContains(response, "Salvar perfil")
        self.assertContains(response, 'disabled aria-disabled="true"')

    def test_second_archived_does_not_count_as_active(self):
        FinancialProfile.objects.create(workspace=self.workspace, name="Arquivo", is_archived=True)
        with self.assertRaisesMessage(ValidationError, "ao menos um perfil ativo"):
            delete_financial_profile(self.owner, self.principal.pk, "CONFIRMAR")

    def test_principal_can_archive_with_another_active(self):
        FinancialProfile.objects.create(workspace=self.workspace, name="Segundo")
        response = self.client.post(self.url, {"action": "toggle_archive"})
        self.assertRedirects(response, reverse("configuracoes-perfis"))
        self.principal.refresh_from_db()
        self.assertTrue(self.principal.is_archived)
        self.assertEqual(FinancialProfile.objects.filter(
            workspace=self.workspace, is_archived=False, deleted_at__isnull=True,
        ).count(), 1)

    def test_principal_can_delete_with_another_active(self):
        FinancialProfile.objects.create(workspace=self.workspace, name="Segundo")
        response = self.client.post(self.url, {
            "action": "delete_profile", "confirm_deletion": "CONFIRMAR",
        })
        self.assertRedirects(response, reverse("configuracoes-perfis"))
        self.principal.refresh_from_db()
        self.assertIsNotNone(self.principal.deleted_at)
        self.assertEqual(FinancialProfile.objects.filter(
            workspace=self.workspace, is_archived=False, deleted_at__isnull=True,
        ).count(), 1)

    def test_after_archiving_second_last_one_is_protected(self):
        second = FinancialProfile.objects.create(workspace=self.workspace, name="Segundo")
        update_financial_profile(self.owner, second.pk, {"is_archived": True})
        with self.assertRaisesMessage(ValidationError, "ao menos um perfil ativo"):
            delete_financial_profile(self.owner, self.principal.pk, "CONFIRMAR")

    def test_another_workspace_does_not_satisfy_minimum(self):
        other = Workspace.objects.create(name="Outra", created_by=self.owner)
        FinancialProfile.objects.create(workspace=other, name="Perfil externo")
        with self.assertRaisesMessage(ValidationError, "ao menos um perfil ativo"):
            delete_financial_profile(self.owner, self.principal.pk, "CONFIRMAR")

    def test_bad_confirmation_cannot_delete_even_with_second_profile(self):
        FinancialProfile.objects.create(workspace=self.workspace, name="Segundo")
        with self.assertRaisesMessage(ValidationError, "Digite CONFIRMAR"):
            delete_financial_profile(self.owner, self.principal.pk, "confirmar")
