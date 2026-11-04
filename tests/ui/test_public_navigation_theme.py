# SPDX-License-Identifier: GPL-3.0-only
"""Canonical public URLs, selected workspace isolation, and per-account theme."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.core.models import UserProfile
from apps.finance.models import FinancialProfile, Workspace, WorkspaceMembership


class CleanNavigationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = get_user_model()
        cls.owner = user.objects.create_user(username='nav-owner', password='safe_test_password_123')
        cls.other = user.objects.create_user(username='nav-other', password='safe_test_password_123')
        cls.workspace = Workspace.objects.create(name='A', created_by=cls.owner)
        cls.foreign = Workspace.objects.create(name='Outro workspace secreto', created_by=cls.other)
        WorkspaceMembership.objects.create(workspace=cls.workspace, user=cls.owner, role='admin')
        WorkspaceMembership.objects.create(workspace=cls.foreign, user=cls.other, role='admin')
        FinancialProfile.objects.create(workspace=cls.workspace, name='Principal')
        FinancialProfile.objects.create(workspace=cls.foreign, name='Outro')

    def setUp(self):
        self.client.force_login(self.owner)

    def test_all_five_canonical_routes_work_without_ids(self):
        for name in ('visao-geral', 'despesas', 'investimentos', 'movimentacoes', 'configuracoes'):
            with self.subTest(route=name):
                url = reverse(name)
                self.assertNotIn('/finance/workspaces/', url)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, 'Outro workspace secreto')

    def test_home_redirects_to_canonical_overview(self):
        response = self.client.get(reverse('home'))
        self.assertRedirects(response, reverse('visao-geral'))

    def test_workspace_selection_rejects_foreign_id(self):
        response = self.client.get(reverse('selecionar-nucleo', args=[self.foreign.pk]))
        self.assertEqual(response.status_code, 403)

    def test_multi_workspace_uses_explicit_selection_not_guessed_id(self):
        second = Workspace.objects.create(name='Segundo da mesma pessoa', created_by=self.owner)
        WorkspaceMembership.objects.create(workspace=second, user=self.owner, role='admin')
        FinancialProfile.objects.create(workspace=second, name='Outra pessoa')
        # No selected workspace: show chooser, not a guessed tenant.
        response = self.client.get(reverse('visao-geral'))
        self.assertRedirects(response, reverse('home'))
        chooser = self.client.get(reverse('home'))
        self.assertContains(chooser, reverse('selecionar-nucleo', args=[second.pk]))
        selected = self.client.get(reverse('selecionar-nucleo', args=[second.pk]))
        self.assertRedirects(selected, reverse('visao-geral'))
        self.assertEqual(self.client.session['alece_workspace_id'], second.pk)
        self.assertEqual(self.client.get(reverse('visao-geral')).status_code, 200)

    def test_sidebar_external_about_and_account_actions_in_settings(self):
        response = self.client.get(reverse('configuracoes'))
        html = response.content.decode()
        self.assertIn('https://caiotomaza.github.io/projetos/alece/', html)
        self.assertNotIn('<h2>Aparência</h2>', html)
        self.assertIn('href="' + reverse('password_change') + '"', html)
        self.assertIn('href="' + reverse('recovery_generate') + '"', html)


class ThemePreferenceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.first = get_user_model().objects.create_user(username='theme-a')
        cls.second = get_user_model().objects.create_user(username='theme-b')
        cls.w1 = Workspace.objects.create(name='Casa 1', created_by=cls.first)
        cls.w2 = Workspace.objects.create(name='Casa 2', created_by=cls.second)
        WorkspaceMembership.objects.create(workspace=cls.w1, user=cls.first, role='admin')
        WorkspaceMembership.objects.create(workspace=cls.w2, user=cls.second, role='admin')
        FinancialProfile.objects.create(workspace=cls.w1, name='P1')
        FinancialProfile.objects.create(workspace=cls.w2, name='P2')

    def test_preference_persists_in_db_and_renders_in_a_new_client(self):
        self.client.force_login(self.first)
        response = self.client.post(reverse('preferencia-tema'), {'theme': 'dark'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(UserProfile.objects.get(user=self.first).theme, 'dark')
        self.assertContains(self.client.get(reverse('visao-geral')), 'data-theme="dark"')
        from django.test import Client
        other_device = Client()
        other_device.force_login(self.first)
        self.assertContains(other_device.get(reverse('visao-geral')), 'data-theme="dark"')

    def test_user_preference_does_not_affect_another_account(self):
        UserProfile.objects.update_or_create(user=self.first, defaults={'theme': 'dark'})
        self.client.force_login(self.second)
        self.assertContains(self.client.get(reverse('visao-geral')), 'data-theme="light"')

    def test_rejects_invalid_theme_and_non_post_requests(self):
        self.client.force_login(self.first)
        self.assertEqual(self.client.post(reverse('preferencia-tema'), {'theme': 'pink'}).status_code, 400)
        self.assertEqual(self.client.get(reverse('preferencia-tema')).status_code, 405)

    def test_anonymous_theme_update_redirects_to_login(self):
        response = self.client.post(reverse('preferencia-tema'), {'theme': 'dark'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/entrar/', response.url)
