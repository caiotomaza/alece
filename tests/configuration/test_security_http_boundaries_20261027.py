# SPDX-License-Identifier: GPL-3.0-only
"""CSRF, escaping e escopo de administradores; usa dados sintéticos."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.core.models import AIProviderConfig
from apps.finance.models import Workspace, WorkspaceMembership


class SecurityHTTPBoundariesTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username="csrf-admin", password="StrongPassword123!")
        self.common = User.objects.create_user(username="csrf-common", password="StrongPassword123!")
        self.workspace = Workspace.objects.create(name="CSRF", created_by=self.admin)
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.admin, role="admin")
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.common, role="common")
        self.provider = AIProviderConfig.objects.create(
            workspace=self.workspace, name="<script>alert(1)</script>",
            endpoint="https://api.openai.com/v1/chat/completions",
            model_name="test", sections=["expenses"], enabled=False,
        )

    def test_admin_post_without_csrf_token_is_forbidden(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        response = client.post(reverse("configuracoes-api-selecionar", args=[self.provider.pk]), {"enabled": "1"})
        self.assertEqual(response.status_code, 403)
        self.provider.refresh_from_db()
        self.assertFalse(self.provider.enabled)

    def test_provider_name_is_escaped_in_html(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("configuracoes-apis"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;")

    def test_common_user_cannot_read_admin_provider_list(self):
        self.client.force_login(self.common)
        response = self.client.get(reverse("configuracoes-apis"))
        self.assertEqual(response.status_code, 403)

    def test_provider_form_never_reprints_secret(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("configuracoes-api-nova"), {
            "provider_type": "custom", "provider_name": "", "endpoint": "",
            "model_name": "", "api_token": "FAKE-CANARY-SECRET-DO-NOT-LOG",
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "FAKE-CANARY-SECRET-DO-NOT-LOG")
