# SPDX-License-Identifier: GPL-3.0-only
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from apps.finance.models import FinancialProfile, Workspace, WorkspaceMembership


class TechnicalReportsRenderingTests(TestCase):
    def test_admin_can_open_reports_dashboard(self):
        user = get_user_model().objects.create_user(username='reports-render-admin')
        workspace = Workspace.objects.create(name='Report UI', created_by=user)
        WorkspaceMembership.objects.create(workspace=workspace, user=user, role='admin')
        FinancialProfile.objects.create(workspace=workspace, name='Principal')
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('relatorios')).status_code, 200)
