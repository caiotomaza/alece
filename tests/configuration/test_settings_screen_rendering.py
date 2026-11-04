# SPDX-License-Identifier: GPL-3.0-only
"""Settings, profile editor and administration rendering smoke checks."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from apps.finance.models import FinancialProfile, Workspace, WorkspaceMembership


class SettingsScreenRenderingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='settings-render-admin')
        cls.workspace = Workspace.objects.create(name='Admin UI', created_by=cls.user)
        WorkspaceMembership.objects.create(workspace=cls.workspace, user=cls.user, role='admin')
        cls.profile = FinancialProfile.objects.create(workspace=cls.workspace, name='Principal')

    def setUp(self):
        self.client.force_login(self.user)

    def test_settings_and_profile_management_render(self):
        self.assertEqual(self.client.get(reverse('configuracoes')).status_code, 200)
        self.assertEqual(self.client.get(reverse('finance:profile-manage', args=[self.profile.pk])).status_code, 200)

    def test_logs_page_renders_for_admin(self):
        response = self.client.get(reverse('logs'))
        self.assertEqual(response.status_code, 200)
