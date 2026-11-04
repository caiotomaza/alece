# SPDX-License-Identifier: GPL-3.0-only
"""Ciclo de vida das chaves: testes com diretório temporário, sem segredos reais."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.core import ai_credentials
from apps.core.ai_credentials import delete_token, has_token, read_token, write_token
from apps.core.models import AIProviderConfig
from apps.finance.models import Workspace, WorkspaceMembership


class CredentialsUnitTests(TestCase):
    def test_rotation_is_atomic_and_revoke_is_idempotent(self):
        with TemporaryDirectory() as dirname, patch.object(ai_credentials, "SECRET_DIR", Path(dirname) / "private"):
            write_token(4, "key-one")
            self.assertEqual(read_token(4), "key-one")
            write_token(4, "key-two")
            self.assertEqual(read_token(4), "key-two")
            self.assertEqual((Path(dirname) / "private" / "provider-4.key").stat().st_mode & 0o777, 0o600)
            self.assertTrue(delete_token(4))
            self.assertFalse(has_token(4))
            self.assertFalse(delete_token(4))

    def test_never_follows_symlink_on_revoke(self):
        with TemporaryDirectory() as dirname, patch.object(ai_credentials, "SECRET_DIR", Path(dirname) / "private"):
            target = Path(dirname) / "outside.key"
            target.write_text("outside-data")
            (Path(dirname) / "private").mkdir()
            (Path(dirname) / "private" / "provider-4.key").symlink_to(target)
            from django.core.exceptions import ImproperlyConfigured
            with self.assertRaises(ImproperlyConfigured):
                delete_token(4)
            self.assertEqual(target.read_text(), "outside-data")


class ProviderViewIsolationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username="ai-security-admin", password="StrongPassword123!")
        self.common = User.objects.create_user(username="ai-security-common", password="StrongPassword123!")
        self.workspace = Workspace.objects.create(name="AI privacy", created_by=self.admin)
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.admin, role="admin")
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.common, role="common")
        self.provider = AIProviderConfig.objects.create(
            workspace=self.workspace, name="IA de teste", endpoint="https://api.openai.com/v1/chat/completions",
            model_name="test-model", sections=["expenses"], enabled=True,
        )

    def test_delete_revokes_private_token(self):
        with TemporaryDirectory() as dirname, patch.object(ai_credentials, "SECRET_DIR", Path(dirname) / "private"):
            write_token(self.provider.pk, "canary-credential")
            self.client.force_login(self.admin)
            response = self.client.post(reverse("configuracoes-api-excluir", args=[self.provider.pk]))
            self.assertEqual(response.status_code, 302)
            self.assertFalse(has_token(self.provider.pk))
            self.assertFalse(AIProviderConfig.objects.filter(pk=self.provider.pk).exists())

    def test_common_cannot_delete_other_users_token(self):
        with TemporaryDirectory() as dirname, patch.object(ai_credentials, "SECRET_DIR", Path(dirname) / "private"):
            write_token(self.provider.pk, "canary-credential")
            self.client.force_login(self.common)
            response = self.client.post(reverse("configuracoes-api-excluir", args=[self.provider.pk]))
            self.assertEqual(response.status_code, 403)
            self.assertTrue(has_token(self.provider.pk))

    def test_ai_requires_explicit_opt_in_before_any_transmission(self):
        self.client.force_login(self.admin)
        with patch("apps.core.settings_views.send_to_ai_provider") as outbound:
            response = self.client.post(reverse("configuracoes-api-analisar", args=[self.provider.pk]), {
                "section": "expenses", "profile": "1", "consent": "no",
            })
        self.assertEqual(response.status_code, 302)
        outbound.assert_not_called()

    def test_consent_copy_lists_scope_and_recipient(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("configuracoes-apis"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data, descrição")
        self.assertContains(response, "api.openai.com")
