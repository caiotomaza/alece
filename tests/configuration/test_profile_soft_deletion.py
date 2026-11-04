# SPDX-License-Identifier: GPL-3.0-only
"""Regression tests for non-destructive profile deletion and access enforcement."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from apps.core.permissions import get_accessible_profiles, user_can_module
from apps.finance.models import BankAccount, FinancialProfile, ProfileGrant, Workspace, WorkspaceMembership
from apps.finance.services.profiles import delete_financial_profile


class ProfileSoftDeletionTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username="archive_admin", password="Example123!")
        self.member = get_user_model().objects.create_user(username="archive_member")
        self.workspace = Workspace.objects.create(name="Casa", created_by=self.admin)
        self.admin_link = WorkspaceMembership.objects.create(
            workspace=self.workspace, user=self.admin, role=WorkspaceMembership.Role.ADMIN,
        )
        self.member_link = WorkspaceMembership.objects.create(
            workspace=self.workspace, user=self.member, role=WorkspaceMembership.Role.COMMON,
        )
        self.profile = FinancialProfile.objects.create(workspace=self.workspace, name="Teste")
        self.standby = FinancialProfile.objects.create(workspace=self.workspace, name="Outro ativo")
        self.grant = ProfileGrant.objects.create(
            profile=self.profile, membership=self.member_link, can_view=True, can_edit=True,
            overview_level=ProfileGrant.Level.EDIT,
        )
        self.account = BankAccount.objects.create(profile=self.profile, name="Conta anterior")

    def test_delete_revokes_grants_and_preserves_financial_references(self):
        self.assertTrue(user_can_module(self.member, self.profile.pk, "overview", "edit"))
        result = delete_financial_profile(self.admin, self.profile.pk, "CONFIRMAR")
        result.refresh_from_db()
        self.assertIsNotNone(result.deleted_at)
        self.assertTrue(result.is_archived)
        self.assertNotEqual(result.name, "Teste")
        self.assertTrue(BankAccount.objects.filter(pk=self.account.pk, profile=result).exists())
        self.grant.refresh_from_db()
        self.assertFalse(self.grant.can_view)
        self.assertFalse(self.grant.can_edit)
        self.assertEqual(self.grant.overview_level, ProfileGrant.Level.NONE)
        self.assertFalse(user_can_module(self.admin, result.pk, "overview"))
        self.assertFalse(user_can_module(self.member, result.pk, "overview"))
        self.assertFalse(get_accessible_profiles(self.admin).filter(pk=result.pk).exists())

    def test_invalid_confirmation_does_not_delete(self):
        with self.assertRaises(ValidationError):
            delete_financial_profile(self.admin, self.profile.pk, "Outro")
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.deleted_at)
        self.assertFalse(self.profile.is_archived)

    def test_non_admin_cannot_delete(self):
        with self.assertRaises(Exception):
            delete_financial_profile(self.member, self.profile.pk, "CONFIRMAR")
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.deleted_at)

    def test_post_deletes_and_redirects_to_settings(self):
        self.client.force_login(self.admin)
        url = reverse("finance:profile-manage", kwargs={"profile_id": self.profile.pk})
        response = self.client.post(url, {"action": "delete_profile", "confirm_deletion": "CONFIRMAR"})
        self.assertEqual(response.status_code, 302)
        self.profile.refresh_from_db()
        self.assertIsNotNone(self.profile.deleted_at)

    def test_http_rejects_profile_name_and_legacy_confirmation_field(self):
        self.client.force_login(self.admin)
        url = reverse("finance:profile-manage", kwargs={"profile_id": self.profile.pk})
        for payload in (
            {"action": "delete_profile", "confirm_deletion": "Teste"},
            {"action": "delete_profile", "confirm_profile_name": "Teste"},
            {"action": "delete_profile", "confirm_deletion": "confirmar"},
            {"action": "delete_profile", "confirm_deletion": ""},
        ):
            with self.subTest(payload=payload):
                response = self.client.post(url, payload)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Digite CONFIRMAR")
                self.profile.refresh_from_db()
                self.assertIsNone(self.profile.deleted_at)
                self.grant.refresh_from_db()
                self.assertTrue(self.grant.can_edit)

    def test_delete_form_requests_uppercase_keyword_not_profile_name(self):
        self.client.force_login(self.admin)
        url = reverse("finance:profile-manage", kwargs={"profile_id": self.profile.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="confirm_deletion"')
        self.assertContains(response, 'pattern="CONFIRMAR"')
        self.assertNotContains(response, 'name="confirm_profile_name"')

    def test_editing_archived_profile_does_not_unarchive_it(self):
        self.client.force_login(self.admin)
        self.profile.is_archived = True
        self.profile.save(update_fields=["is_archived"])
        url = reverse("finance:profile-manage", kwargs={"profile_id": self.profile.pk})
        response = self.client.post(url, {"action": "profile", "name": "Nome alterado", "emoji": ""})
        self.assertEqual(response.status_code, 302)
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.is_archived)
        self.assertEqual(self.profile.name, "Nome alterado")
