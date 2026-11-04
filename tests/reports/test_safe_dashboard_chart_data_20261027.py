# SPDX-License-Identifier: GPL-3.0-only
"""Garante que nomes de investimentos não sejam interpolados em JavaScript executável."""
import json
import re

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.finance.models import FinancialProfile, InvestmentPosition, Workspace, WorkspaceMembership


class FinancialDashboardChartSafetyTests(TestCase):
    def test_chart_data_is_minimized_json_and_cannot_break_out_of_script(self):
        user = get_user_model().objects.create_user(username="chart-security-admin")
        workspace = Workspace.objects.create(name="Gráficos", created_by=user)
        WorkspaceMembership.objects.create(workspace=workspace, user=user, role="admin")
        profile = FinancialProfile.objects.create(workspace=workspace, name="Principal")
        malicious_name = "</script><script>alert('xss')</script>"
        InvestmentPosition.objects.create(
            profile=profile, name=malicious_name, category="patrimony",
            applied_amount="10.00", current_value="12.50",
        )
        self.client.force_login(user)
        response = self.client.get(reverse("finance:reports-dashboard", args=[workspace.pk]))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertNotIn(malicious_name, html)
        self.assertNotIn("dashboard.investments|safe", html)
        self.assertNotIn("const inv = ", html)
        match = re.search(
            r'<script id="alece-chart-investments" type="application/json">(.*?)</script>',
            html, flags=re.DOTALL,
        )
        self.assertIsNotNone(match)
        self.assertIn(r"\u003C/script\u003E", match.group(1))
        chart_data = json.loads(match.group(1))
        self.assertEqual(chart_data, [{"name": malicious_name, "current_value": "12.50"}])
        equity = re.search(
            r'<script id="alece-chart-equity" type="application/json">(.*?)</script>',
            html, flags=re.DOTALL,
        )
        self.assertIsNotNone(equity)
        self.assertIn("net_equity", json.loads(equity.group(1))[0])

    def test_ungranted_user_does_not_receive_chart_json(self):
        User = get_user_model()
        owner = User.objects.create_user(username="chart-owner")
        other = User.objects.create_user(username="chart-outsider")
        workspace = Workspace.objects.create(name="Reservado", created_by=owner)
        WorkspaceMembership.objects.create(workspace=workspace, user=owner, role="admin")
        profile = FinancialProfile.objects.create(workspace=workspace, name="Privado")
        self.client.force_login(other)
        response = self.client.get(reverse("finance:reports-dashboard", args=[workspace.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(b"alece-chart-equity", response.content)
