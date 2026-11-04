# SPDX-License-Identifier: GPL-3.0-only
"""Regression with an isolated Django test database (PostgreSQL recommended)."""
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase, SimpleTestCase
from django.urls import reverse
from apps.core.ai_catalog import PROVIDERS
from apps.core.models import AIProviderConfig
from apps.core.settings_forms import AIProviderConfigForm
from apps.finance.models import Workspace, WorkspaceMembership


class AiPresetFieldTests(SimpleTestCase):
    def test_preset_ignores_submitted_endpoint_and_model(self):
        form = AIProviderConfigForm({
            'provider_type': 'openai', 'provider_name': 'Ataque',
            'endpoint': 'https://attacker.example/chat/completions',
            'model_name': 'fake', 'api_token': 'sample-test-key', 'enabled': 'on',
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['endpoint'], PROVIDERS['openai']['endpoint'])
        self.assertEqual(form.cleaned_data['model_name'], PROVIDERS['openai']['model'])
        self.assertEqual(form.cleaned_data['provider_name'], PROVIDERS['openai']['name'])
        self.assertTrue(form.cleaned_data['enabled'])

    def test_custom_requires_https_name_model_and_token(self):
        form = AIProviderConfigForm({'provider_type': 'custom', 'api_token': 'sample-test-key',
                                     'endpoint': 'http://api.example.com', 'model_name': 'test'})
        self.assertFalse(form.is_valid())
        self.assertIn('provider_name', form.errors)
        self.assertIn('endpoint', form.errors)
        good = AIProviderConfigForm({'provider_type':'custom', 'api_token':'sample-test-key',
                                     'endpoint':'https://api.example.com/v1/chat/completions',
                                     'model_name':'model-1', 'provider_name':'Minha IA'})
        self.assertTrue(good.is_valid(), good.errors)


class AiSingleActiveDBTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user('ai-owner', password='Test-key-12345')
        cls.workspace = Workspace.objects.create(name='AI workspace', created_by=cls.owner)
        WorkspaceMembership.objects.create(workspace=cls.workspace, user=cls.owner, role='admin')
        cls.first = AIProviderConfig.objects.create(
            workspace=cls.workspace, name='First', endpoint=PROVIDERS['openai']['endpoint'],
            model_name=PROVIDERS['openai']['model'], sections=['expenses','investments','movements'], enabled=True,
        )
        cls.second = AIProviderConfig.objects.create(
            workspace=cls.workspace, name='Second', endpoint=PROVIDERS['gemini']['endpoint'],
            model_name=PROVIDERS['gemini']['model'], sections=['expenses','investments','movements'], enabled=False,
        )

    def test_database_rejects_two_active_in_one_workspace(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AIProviderConfig.objects.filter(pk=self.second.pk).update(enabled=True)

    def test_selecting_new_deactivates_previous(self):
        from apps.core.settings_views import _set_active_ai_provider_locked
        with transaction.atomic():
            Workspace.objects.select_for_update().get(pk=self.workspace.pk)
            _set_active_ai_provider_locked(self.workspace, self.second.pk)
        self.assertFalse(AIProviderConfig.objects.get(pk=self.first.pk).enabled)
        self.assertTrue(AIProviderConfig.objects.get(pk=self.second.pk).enabled)
        self.assertEqual(AIProviderConfig.objects.filter(workspace=self.workspace,enabled=True).count(),1)

    def test_activation_requires_token_and_permission(self):
        self.client.force_login(self.owner)
        with patch('apps.core.settings_views._ai_provider_is_ready',return_value=True):
            response = self.client.post(reverse('configuracoes-api-selecionar', args=[self.second.pk]), {'enabled':'1'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(AIProviderConfig.objects.filter(workspace=self.workspace,enabled=True).count(),1)
        self.assertTrue(AIProviderConfig.objects.get(pk=self.second.pk).enabled)

    def test_prevent_activation_without_credentials(self):
        self.client.force_login(self.owner)
        with patch('apps.core.settings_views._ai_provider_is_ready', return_value=False):
            response = self.client.post(reverse('configuracoes-api-selecionar', args=[self.second.pk]), {'enabled':'1'})
        self.assertEqual(response.status_code,302)
        self.assertFalse(AIProviderConfig.objects.get(pk=self.second.pk).enabled)
        self.assertTrue(AIProviderConfig.objects.get(pk=self.first.pk).enabled)

    def test_common_user_cannot_change_selected_provider(self):
        common = get_user_model().objects.create_user('api-common', password='Test-common-12345')
        WorkspaceMembership.objects.create(workspace=self.workspace, user=common, role='common')
        self.client.force_login(common)
        response = self.client.post(reverse('configuracoes-api-selecionar', args=[self.second.pk]), {'enabled':'1'})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(AIProviderConfig.objects.get(pk=self.second.pk).enabled)
