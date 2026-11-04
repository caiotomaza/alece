# SPDX-License-Identifier: GPL-3.0-only
"""Páginas de gestão: navegação integral e isolamento de acesso no servidor.

Executar com Django + PostgreSQL de testes, não no banco de produção.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from apps.finance.models import Workspace, WorkspaceMembership, FinancialProfile


class AdminManagementPagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user('management-admin', password='test-pass-123')
        cls.common = get_user_model().objects.create_user('management-common', password='test-pass-123')
        cls.workspace = Workspace.objects.create(name='Gestão Teste', created_by=cls.admin)
        WorkspaceMembership.objects.create(workspace=cls.workspace, user=cls.admin, role='admin')
        WorkspaceMembership.objects.create(workspace=cls.workspace, user=cls.common, role='common')
        FinancialProfile.objects.create(workspace=cls.workspace, name='Principal')

    def test_administrative_shortcuts_navigate_to_independent_pages(self):
        self.client.force_login(self.admin)
        landing = self.client.get(reverse('configuracoes'))
        self.assertEqual(landing.status_code, 200)
        for route in ('configuracoes-usuarios', 'configuracoes-perfis', 'configuracoes-apis'):
            with self.subTest(route=route):
                self.assertContains(landing, 'href="' + reverse(route) + '"')
                response = self.client.get(reverse(route))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'settings-management-intro')
                self.assertContains(response, 'settings-management-shell')
                self.assertContains(response, reverse('configuracoes'))
                self.assertNotContains(response, 'data-dialog-content')
                self.assertNotContains(response, 'data-edit-dialog')

    def test_common_user_cannot_open_admin_management_pages(self):
        self.client.force_login(self.common)
        self.assertEqual(self.client.get(reverse('configuracoes')).status_code, 200)
        for route in ('configuracoes-usuarios', 'configuracoes-perfis', 'configuracoes-apis'):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(reverse(route)).status_code, 403)

    def test_admin_page_does_not_automatically_create_or_modify_data(self):
        self.client.force_login(self.admin)
        before = WorkspaceMembership.objects.count()
        for route in ('configuracoes-usuarios', 'configuracoes-perfis', 'configuracoes-apis'):
            self.assertEqual(self.client.get(reverse(route)).status_code, 200)
        self.assertEqual(WorkspaceMembership.objects.count(), before)
