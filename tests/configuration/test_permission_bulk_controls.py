# SPDX-License-Identifier: GPL-3.0-only
"""Regression tests for consistent permission bulk controls and saved grants."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from apps.finance.models import FinancialProfile, ProfileGrant, Workspace, WorkspaceMembership


@override_settings(ALECE_REQUIRE_RECOVERY_SETUP=False)
class PermissionBulkTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user("bulk-admin", password="TestPassword123")
        cls.user = User.objects.create_user("bulk-member", password="TestPassword123")
        cls.other = User.objects.create_user("other-admin", password="TestPassword123")
        cls.workspace = Workspace.objects.create(name="Pessoal", created_by=cls.admin)
        cls.member = WorkspaceMembership.objects.create(workspace=cls.workspace, user=cls.user, role="common")
        WorkspaceMembership.objects.create(workspace=cls.workspace, user=cls.admin, role="admin")
        cls.profile = FinancialProfile.objects.create(workspace=cls.workspace, name="Principal")

    def url(self):
        return reverse("core:grant-management", args=[self.workspace.pk, self.member.pk])

    def post_data(self, **overrides):
        data = {f"grant_{self.profile.pk}_{field}_level": "view" for field in (
            "overview", "accounts", "expenses", "investments", "movements"
        )}
        data.update(overrides)
        return data

    def test_all_edit_from_five_selected_levels(self):
        self.client.force_login(self.admin)
        data = {key: "edit" for key in self.post_data()}
        data[f"grant_{self.profile.pk}_can_edit"] = "on"
        self.assertEqual(self.client.post(self.url(), data).status_code, 302)
        grant = ProfileGrant.objects.get(profile=self.profile, membership=self.member)
        self.assertTrue(grant.can_view)
        self.assertTrue(grant.can_edit)
        for field in ("overview", "accounts", "expenses", "investments", "movements"):
            self.assertEqual(getattr(grant, field + "_level"), "edit")
        html = self.client.get(reverse("core:user-edit", args=[self.workspace.pk, self.user.pk])).content.decode()
        self.assertIn('data-grant-bulk="edit" checked', html)

    def test_mixed_grants_are_not_misrepresented_as_full_access(self):
        self.client.force_login(self.admin)
        data = self.post_data(**{f"grant_{self.profile.pk}_expenses_level": "edit",
                                 f"grant_{self.profile.pk}_accounts_level": "none"})
        data[f"grant_{self.profile.pk}_can_edit"] = "on"
        self.assertEqual(self.client.post(self.url(), data).status_code, 302)
        grant = ProfileGrant.objects.get(profile=self.profile, membership=self.member)
        self.assertTrue(grant.can_edit)
        self.assertTrue(grant.can_view)
        response = self.client.get(reverse("core:user-edit", args=[self.workspace.pk, self.user.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-grant-bulk="edit"')
        self.assertNotContains(response, 'data-grant-bulk="edit" checked')
        self.assertNotContains(response, 'data-grant-bulk="view" checked')

    def test_server_ignores_forged_bulk_boxes_when_levels_denied(self):
        self.client.force_login(self.admin)
        data = {key: "none" for key in self.post_data()}
        data[f"grant_{self.profile.pk}_can_edit"] = "on"
        data[f"grant_{self.profile.pk}_can_view"] = "on"
        self.assertEqual(self.client.post(self.url(), data).status_code, 302)
        grant = ProfileGrant.objects.get(profile=self.profile, membership=self.member)
        self.assertFalse(grant.can_edit)
        self.assertFalse(grant.can_view)

    def test_rejects_invalid_levels_without_partial_updates(self):
        self.client.force_login(self.admin)
        data = self.post_data(**{f"grant_{self.profile.pk}_movements_level": "invalid"})
        self.assertEqual(self.client.post(self.url(), data).status_code, 400)
        self.assertFalse(ProfileGrant.objects.filter(profile=self.profile, membership=self.member).exists())

    def test_common_cannot_modify_any_grants(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(self.url(), self.post_data()).status_code, 403)
