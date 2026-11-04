# SPDX-License-Identifier: GPL-3.0-only
"""Rendering smoke tests for finance pages, backed by isolated test DB."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from apps.finance.models import FinancialProfile, Workspace, WorkspaceMembership


class FinanceScreenRenderingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='finance-render-admin')
        cls.workspace = Workspace.objects.create(name='Finance UI', created_by=cls.user)
        WorkspaceMembership.objects.create(workspace=cls.workspace, user=cls.user, role='admin')
        cls.profile = FinancialProfile.objects.create(workspace=cls.workspace, name='Principal')

    def setUp(self):
        self.client.force_login(self.user)

    def test_dashboard_expenses_investments_movements_render(self):
        for name in ('visao-geral', 'despesas', 'investimentos', 'movimentacoes'):
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)

    def test_expense_and_investment_crud_forms_render(self):
        for name in ('recurring-create', 'investment-create'):
            with self.subTest(name=name):
                response = self.client.get(reverse(f'finance:{name}', args=[self.profile.pk]))
                self.assertEqual(response.status_code, 200)
