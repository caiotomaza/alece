# SPDX-License-Identifier: GPL-3.0-only
"""Regression tests requiring Django + isolated test PostgreSQL."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.models import AIAnalysis, AIProviderConfig, UserProfile
from apps.finance.models import FinancialProfile, Workspace, WorkspaceMembership


class SettingsRolesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user("settings-admin", password="Admin-pass-test-123")
        cls.common = User.objects.create_user("settings-user", password="Common-pass-test-123")
        cls.other = User.objects.create_user("settings-outsider", password="Other-pass-test-123")
        cls.workspace = Workspace.objects.create(name="Família", created_by=cls.owner)
        cls.foreign = Workspace.objects.create(name="Secreto", created_by=cls.other)
        WorkspaceMembership.objects.create(user=cls.owner, workspace=cls.workspace, role="admin")
        WorkspaceMembership.objects.create(user=cls.common, workspace=cls.workspace, role="common")
        WorkspaceMembership.objects.create(user=cls.other, workspace=cls.foreign, role="admin")
        cls.profile = FinancialProfile.objects.create(name="Pessoa", workspace=cls.workspace)
        cls.foreign_profile = FinancialProfile.objects.create(name="Secreto pessoa", workspace=cls.foreign)
        cls.config = AIProviderConfig.objects.create(
            workspace=cls.workspace, name="IA A", endpoint="https://api.example.com/v1/chat/completions",
            model_name="model-a", api_key_env="ALECE_AI_TEST_KEY", sections=["expenses"], enabled=True,
        )

    def test_common_only_sees_personal_settings(self):
        self.client.force_login(self.common)
        response = self.client.get(reverse("configuracoes"))
        self.assertEqual(response.status_code, 200)
        for action in ("Editar suas informações", "Resetar sua senha", "Resetar seus códigos de recuperação"):
            self.assertContains(response, action)
        self.assertNotContains(response, "Gerenciar usuários")
        self.assertNotContains(response, "Gerenciar perfis financeiros")
        self.assertNotContains(response, "Gerenciar APIs de IA")
        self.assertNotContains(response, self.config.name)
        for route in ("configuracoes-usuarios", "configuracoes-perfis", "configuracoes-apis"):
            self.assertEqual(self.client.get(reverse(route)).status_code, 403)

    def test_admin_sees_shortcuts_not_embedded_tables(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("configuracoes"))
        self.assertEqual(response.status_code, 200)
        for action in ("Gerenciar usuários", "Gerenciar perfis financeiros", "Gerenciar APIs de IA", "Visualizar logs", "Relatórios, backups e importações"):
            self.assertContains(response, action)
        self.assertNotContains(response, self.config.name)
        self.assertNotContains(response, "Secreto pessoa")
        for name, expected in (("configuracoes-usuarios", "Usuários cadastrados"), ("configuracoes-perfis", "Pessoa"), ("configuracoes-apis", "IA A")):
            panel = self.client.get(reverse(name))
            self.assertEqual(panel.status_code, 200)
            self.assertContains(panel, 'settings-management-intro')
            self.assertContains(panel, 'settings-management-shell')
            self.assertNotContains(panel, 'data-dialog-content')
            self.assertContains(panel, expected)
            self.assertNotContains(panel, "Secreto pessoa")
        landing = response.content.decode('utf-8')
        for name in ('configuracoes-usuarios', 'configuracoes-perfis', 'configuracoes-apis'):
            self.assertIn('href="' + reverse(name) + '"', landing)
        self.assertNotIn('settings-action-card settings-modal-trigger', landing.split('id="settings-admin"', 1)[-1])

    def test_common_cannot_open_api_management_or_send_analysis(self):
        self.client.force_login(self.common)
        self.assertEqual(self.client.get(reverse("configuracoes-api-nova")).status_code, 403)
        self.assertEqual(self.client.get(reverse("configuracoes-api-editar", args=[self.config.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("configuracoes-api-excluir", args=[self.config.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("configuracoes-api-analisar", args=[self.config.pk]), {
            "section": "expenses", "profile": str(self.profile.pk), "consent": "yes",
        }).status_code, 403)
        self.assertTrue(AIProviderConfig.objects.filter(pk=self.config.pk, enabled=True).exists())

    def test_admin_cannot_edit_provider_owned_by_another_workspace(self):
        foreign_provider = AIProviderConfig.objects.create(
            workspace=self.foreign, name="IA secreta", endpoint="https://api.example.com/v1/chat/completions",
            model_name="a", sections=["expenses"], enabled=True,
        )
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(reverse("configuracoes-api-editar", args=[foreign_provider.pk])).status_code, 404)

    def test_personal_information_requires_current_password(self):
        self.client.force_login(self.common)
        url = reverse("configuracoes-minha-conta")
        data = {"username": "settings-user", "first_name": "Novo", "last_name": "Nome", "email": "user@example.com", "current_password": "wrong"}
        self.assertEqual(self.client.post(url, data).status_code, 200)
        self.common.refresh_from_db()
        self.assertEqual(self.common.first_name, "")
        data["current_password"] = "Common-pass-test-123"
        self.assertRedirects(self.client.post(url, data), reverse("configuracoes"))
        self.common.refresh_from_db()
        self.assertEqual(self.common.first_name, "Novo")

    def test_recovery_lookup_redirects_after_acknowledgment_without_exposing_codes(self):
        from apps.core.auth_services import issue_recovery_codes, acknowledge_recovery_codes
        self.client.force_login(self.common)
        codes = issue_recovery_codes(self.common.pk, "Common-pass-test-123")
        self.assertTrue(acknowledge_recovery_codes(self.common.pk))
        response = self.client.get(reverse("configuracoes-codigos"))
        self.assertRedirects(response, reverse("configuracoes"), fetch_redirect_response=False)
        for code in codes:
            self.assertNotIn(code, response.content.decode("utf-8"))

    def test_admin_cannot_analyze_foreign_financial_profile(self):
        self.client.force_login(self.owner)
        with patch("apps.core.settings_views.send_to_ai_provider") as mock_send:
            response = self.client.post(reverse("configuracoes-api-analisar", args=[self.config.pk]), {
                "profile": self.foreign_profile.pk, "section": "expenses", "consent": "yes",
            })
        self.assertEqual(response.status_code, 404)
        mock_send.assert_not_called()

    def test_ai_analysis_requires_explicit_consent(self):
        self.client.force_login(self.owner)
        with patch("apps.core.settings_views.send_to_ai_provider") as mock_send:
            response = self.client.post(reverse("configuracoes-api-analisar", args=[self.config.pk]), {
                "profile": self.profile.pk, "section": "expenses",
            })
        self.assertRedirects(response, reverse("configuracoes-apis"))
        mock_send.assert_not_called()
        self.assertFalse(AIAnalysis.objects.exists())

    def test_provider_host_is_not_persistently_allowed_by_default(self):
        from django.core.exceptions import ValidationError
        from apps.core.ai_service import send_to_ai_provider
        with patch.dict("os.environ", {"ALECE_AI_ALLOWED_HOSTS": ""}, clear=False):
            with self.assertRaises(ValidationError):
                send_to_ai_provider(self.config, {"records": []})

    def test_outbound_rejects_plain_http_and_local_addresses(self):
        from apps.core.settings_forms import AIProviderConfigForm
        for malicious in ("https://localhost/", "https://127.0.0.1/", "http://api.example.com/"):
            with self.subTest(url=malicious):
                form = AIProviderConfigForm({"provider_type": malicious, "api_token": "token-test"})
                self.assertFalse(form.is_valid())
