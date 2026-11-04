# SPDX-License-Identifier: GPL-3.0-only
"""New mandatory recovery-flow regressions. Runs with Django/PostgreSQL in CI."""
import re

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.auth_services import (
    acknowledge_recovery_codes, issue_recovery_codes, redeem_recovery_code,
)
from apps.core.models import RecoveryCode, UserProfile
from apps.finance.models import FinancialProfile, Workspace, WorkspaceMembership


@override_settings(ALECE_REQUIRE_RECOVERY_SETUP=True)
class RecoveryEnrollmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user("recovery-v2", password="Known-old-password-42")
        cls.workspace = Workspace.objects.create(name="Pessoal", created_by=cls.user)
        WorkspaceMembership.objects.create(user=cls.user, workspace=cls.workspace, role="admin")
        FinancialProfile.objects.create(name="Principal", workspace=cls.workspace)

    def setUp(self):
        self.client.force_login(self.user)

    def test_first_access_requires_six_codes_and_download_copy(self):
        self.assertRedirects(self.client.get(reverse("configuracoes")),
                             reverse("configuracoes-codigos"), fetch_redirect_response=False)
        result = self.client.get(reverse("configuracoes-codigos"))
        self.assertEqual(result.status_code, 200)
        codes = result.context["codes"]
        self.assertEqual(len(codes), 6)
        self.assertEqual(len(set(codes)), 6)
        self.assertTrue(all(re.fullmatch(r"[A-Z2-9]{8}", c) for c in codes))
        self.assertEqual(RecoveryCode.objects.filter(user=self.user).count(), 6)
        hashes = list(RecoveryCode.objects.filter(user=self.user).values_list("code_hash", flat=True))
        for code in codes:
            self.assertNotIn(code, hashes)
        nonce = result.context["nonce"]
        url = reverse("configuracoes-codigos")
        self.assertIsNone(UserProfile.objects.get(user=self.user).recovery_acknowledged_at)
        self.assertRedirects(self.client.post(url, {"nonce": nonce, "copied": "1", "downloaded": "1"}),
                             reverse("configuracoes"), fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse("configuracoes")).status_code, 200)
        self.assertIn("no-store", result.headers["Cache-Control"])
        state = self.client.get(url)
        self.assertRedirects(state, reverse("configuracoes"), fetch_redirect_response=False)
        self.assertFalse(any(code in state.content.decode("utf-8") for code in codes))

    def test_recovery_modal_is_consistent_and_does_not_reveal_old_codes(self):
        url = reverse("configuracoes-codigos")
        first = self.client.get(url)
        self.assertEqual(first.status_code, 200)
        self.assertContains(first, 'class="dialog-fallback recovery-modal-body"')
        for marker in ('data-recovery-copy', 'data-recovery-download', 'data-recovery-code'):
            self.assertContains(first, marker)
        codes = first.context["codes"]
        nonce = first.context["nonce"]
        self.client.post(url, {"nonce": nonce, "copied": "1", "downloaded": "1"})
        later = self.client.get(url)
        self.assertRedirects(later, reverse("configuracoes"), fetch_redirect_response=False)
        for code in codes:
            self.assertNotIn(code, later.content.decode("utf-8"))
        self.assertEqual(RecoveryCode.objects.filter(user=self.user, used_at__isnull=True).count(), 6)
        settings_page = self.client.get(reverse("configuracoes"))
        self.assertNotContains(settings_page, "Ver códigos de recuperação")
        self.assertContains(settings_page, "Resetar códigos de recuperação")

    def test_interrupted_issuance_does_not_show_status_only_modal(self):
        url = reverse("configuracoes-codigos")
        initial = self.client.get(url)
        self.assertEqual(initial.status_code, 200)
        codes = initial.context["codes"]
        interrupted = self.client.get(url)
        self.assertRedirects(interrupted, reverse("recovery_generate"), fetch_redirect_response=False)
        self.assertEqual(RecoveryCode.objects.filter(user=self.user).count(), 6)
        for code in codes:
            self.assertNotIn(code, interrupted.content.decode("utf-8"))

    def test_user_profile_helper_uses_related_user_for_recovery_codes(self):
        profile = UserProfile.objects.get(user=self.user)
        self.assertFalse(profile.has_recovery_code())
        issue_recovery_codes(self.user.pk, "Known-old-password-42")
        self.assertTrue(profile.has_recovery_code())
        self.assertTrue(acknowledge_recovery_codes(self.user.pk))
        self.assertEqual(self.client.get(reverse("configuracoes")).status_code, 200)
        self.assertEqual(self.client.get(reverse("visao-geral")).status_code, 200)

    def test_each_code_is_single_use_while_other_five_survive(self):
        codes = issue_recovery_codes(self.user.pk, "Known-old-password-42")
        self.assertTrue(acknowledge_recovery_codes(self.user.pk))
        result, errors = redeem_recovery_code(self.user.username, codes[0], {
            "new_password1": "New-high-security-password-42",
            "new_password2": "New-high-security-password-42",
        })
        self.assertTrue(result, errors)
        self.assertEqual(RecoveryCode.objects.filter(user=self.user, used_at__isnull=True).count(), 5)
        self.assertFalse(redeem_recovery_code(self.user.username, codes[0], {
            "new_password1": "Another-password-42", "new_password2": "Another-password-42",
        })[0])
        self.assertTrue(RecoveryCode.objects.filter(user=self.user, used_at__isnull=True).count() == 5)

    def test_password_change_is_valid_modal_with_three_fields(self):
        issue_recovery_codes(self.user.pk, "Known-old-password-42")
        acknowledge_recovery_codes(self.user.pk)
        response = self.client.get(reverse("password_change"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-dialog-content')
        for field in ("old_password", "new_password1", "new_password2"):
            self.assertContains(response, 'name="' + field + '"')
        response = self.client.post(reverse("password_change"), {
            "old_password": "Known-old-password-42", "new_password1": "New-great-password-42",
            "new_password2": "New-great-password-42",
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("New-great-password-42"))

    def test_reset_requires_current_password_and_revokes_old_set(self):
        original = issue_recovery_codes(self.user.pk, "Known-old-password-42")
        acknowledge_recovery_codes(self.user.pk)
        self.client.post(reverse("recovery_generate"), {"current_password": "wrong"})
        self.assertEqual(RecoveryCode.objects.filter(user=self.user).count(), 6)
        new_response = self.client.post(reverse("recovery_generate"), {
            "current_password": "Known-old-password-42"
        })
        self.assertEqual(new_response.status_code, 200)
        self.assertEqual(len(new_response.context["codes"]), 6)
        self.assertIsNone(UserProfile.objects.get(user=self.user).recovery_acknowledged_at)
        self.assertFalse(redeem_recovery_code(self.user.username, original[0], {
            "new_password1": "New-great-password-42", "new_password2": "New-great-password-42",
        })[0])

    def test_user_table_has_only_one_edit_control_and_admin_modal(self):
        issue_recovery_codes(self.user.pk, "Known-old-password-42")
        acknowledge_recovery_codes(self.user.pk)
        second = get_user_model().objects.create_user("recovery-second", password="Another-strong-pass-42")
        WorkspaceMembership.objects.create(user=second, workspace=self.workspace, role="common")
        dashboard = self.client.get(reverse("configuracoes"))
        self.assertEqual(dashboard.status_code, 200)
        self.assertContains(dashboard, 'aria-label="Criar usuário"')
        self.assertContains(dashboard, 'aria-label="Editar usuário recovery-second"')
        self.assertNotContains(dashboard, 'aria-label="Redefinir senha de recovery-second"')
        modal = self.client.get(reverse("core:user-edit", args=[self.workspace.pk, second.pk]))
        self.assertEqual(modal.status_code, 200)
        for text in ("Dados da conta", "Permissões em perfis financeiros", "Recuperação de conta",
                     "Redefinição administrativa de senha", "Excluir usuário do núcleo"):
            self.assertContains(modal, text)

    def test_last_admin_and_self_removal_protected(self):
        issue_recovery_codes(self.user.pk, "Known-old-password-42")
        acknowledge_recovery_codes(self.user.pk)
        response = self.client.post(reverse("core:user-remove-access", args=[self.workspace.pk, self.user.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(WorkspaceMembership.objects.filter(user=self.user, workspace=self.workspace).exists())
