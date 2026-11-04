# SPDX-License-Identifier: GPL-3.0-only
"""Regressions for account lifecycle, irreversible erasure, and unified modal actions."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.models import UserProfile, RecoveryCode, SystemLog
from apps.core.auth_services import issue_recovery_codes, acknowledge_recovery_codes
from apps.finance.models import Workspace, WorkspaceMembership, FinancialProfile


@override_settings(ALECE_REQUIRE_RECOVERY_SETUP=False)
class AccountLifecycleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(username="admin-test", password="PassAdmin2026")
        cls.target = get_user_model().objects.create_user(username="teste", password="PassUser2026", email="teste@example.test")
        cls.workspace = Workspace.objects.create(name="Pessoal", created_by=cls.admin)
        WorkspaceMembership.objects.create(user=cls.admin, workspace=cls.workspace, role="admin")
        cls.member = WorkspaceMembership.objects.create(user=cls.target, workspace=cls.workspace, role="common")
        cls.profile = FinancialProfile.objects.create(workspace=cls.workspace, name="Principal")
        UserProfile.objects.get_or_create(user=cls.target)

    def setUp(self):
        self.client.force_login(self.admin)

    def _url(self, name):
        return reverse(name, kwargs={"workspace_id":self.workspace.pk,"user_id":self.target.pk})

    def test_modal_displays_code_count_not_secrets_and_has_separate_form_targets(self):
        codes = issue_recovery_codes(self.target.pk, "PassUser2026")
        acknowledge_recovery_codes(self.target.pk)
        response = self.client.get(self._url("core:user-edit"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "6 disponíveis")
        self.assertContains(response, "Códigos de recuperação")
        self.assertContains(response, 'data-confirm-user-deletion')
        self.assertContains(response, self._url("core:user-delete-account"))
        self.assertContains(response, reverse("core:grant-management", kwargs={"workspace_id":self.workspace.pk,"membership_id":self.member.pk}))
        for code in codes:
            self.assertNotContains(response, code)

    def test_deactivate_and_reactivate_common_account_with_single_admin(self):
        url = self._url("core:user-edit")
        self.assertEqual(self.client.post(url,{"username":"teste","role":"common"}).status_code, 302)
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_active)
        self.assertEqual(self.client.post(url,{"username":"teste","role":"common","is_active":"on"}).status_code, 302)
        self.target.refresh_from_db()
        self.assertTrue(self.target.is_active)

    def test_delete_requires_exact_confirmation_and_preserves_history(self):
        url = self._url("core:user-delete-account")
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url,{"confirm_username":"wrong","confirmation":"excluir"}).status_code, 302)
        self.assertTrue(WorkspaceMembership.objects.filter(pk=self.member.pk).exists())
        # This protected attribution must remain attached to a valid user row.
        self.workspace.created_by = self.target
        self.workspace.save(update_fields=["created_by"])
        self.assertEqual(self.client.post(url,{"confirm_username":"teste","confirmation":"excluir"}).status_code, 302)
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_active)
        self.assertFalse(self.target.has_usable_password())
        self.assertEqual(self.target.email, "")
        self.assertTrue(self.target.username.startswith("excluido_"))
        self.assertFalse(WorkspaceMembership.objects.filter(pk=self.member.pk).exists())
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.created_by_id, self.target.pk)
        self.assertTrue(SystemLog.objects.filter(object_type="User", object_id=str(self.target.pk)).exists())

    def test_cannot_delete_user_with_other_workspace_membership(self):
        other = Workspace.objects.create(name="Segundo", created_by=self.admin)
        WorkspaceMembership.objects.create(user=self.target, workspace=other, role="common")
        response = self.client.post(self._url("core:user-delete-account"),{"confirmation":"excluir", "confirm_username":"teste"})
        self.assertEqual(response.status_code, 403)
        self.target.refresh_from_db()
        self.assertEqual(self.target.username, "teste")
        self.assertTrue(self.target.is_active)

    def test_common_user_cannot_delete_another_account(self):
        self.client.force_login(self.target)
        response = self.client.post(reverse("core:user-delete-account",kwargs={"workspace_id":self.workspace.pk,"user_id":self.admin.pk}),{"confirmation":"excluir", "confirm_username":"admin-test"})
        self.assertEqual(response.status_code,403)

    def test_admin_cannot_delete_self(self):
        response = self.client.post(reverse("core:user-delete-account",kwargs={"workspace_id":self.workspace.pk,"user_id":self.admin.pk}),{"confirmation":"excluir", "confirm_username":"admin-test"})
        self.assertEqual(response.status_code,403)
