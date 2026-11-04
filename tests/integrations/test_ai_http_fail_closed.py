# SPDX-License-Identifier: GPL-3.0-only
"""Provider-changing endpoints never accept GET or non-admin mutations."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from apps.core.models import AIProviderConfig
from apps.finance.models import Workspace, WorkspaceMembership


class AIHTTPAccessTests(TestCase):
    def setUp(self):
        user=get_user_model()
        self.admin=user.objects.create_user(username="provider-http-admin",password="Unreal12345!")
        self.common=user.objects.create_user(username="provider-http-common",password="Unreal12345!")
        self.workspace=Workspace.objects.create(name="IA HTTP",created_by=self.admin)
        WorkspaceMembership.objects.create(workspace=self.workspace,user=self.admin,role="admin")
        WorkspaceMembership.objects.create(workspace=self.workspace,user=self.common,role="common")
        self.provider=AIProviderConfig.objects.create(workspace=self.workspace,name="Configuração sintética",endpoint="https://example.com/v1/chat/completions",model_name="test",sections=["expenses"],enabled=False)

    def test_activation_endpoint_is_post_only(self):
        self.client.force_login(self.admin)
        for name in ("configuracoes-api-selecionar","configuracoes-api-excluir","configuracoes-api-analisar"):
            with self.subTest(name=name):
                response=self.client.get(reverse(name,args=[self.provider.pk]))
                self.assertEqual(response.status_code,405)
        self.assertFalse(AIProviderConfig.objects.get(pk=self.provider.pk).enabled)

    def test_common_user_cannot_activate_even_with_forged_post(self):
        self.client.force_login(self.common)
        resp=self.client.post(reverse("configuracoes-api-selecionar",args=[self.provider.pk]), {"enabled":"1"})
        self.assertEqual(resp.status_code,403)
        self.assertFalse(AIProviderConfig.objects.get(pk=self.provider.pk).enabled)

    def test_invalid_state_rejected_and_no_provider_enabled(self):
        self.client.force_login(self.admin)
        resp=self.client.post(reverse("configuracoes-api-selecionar",args=[self.provider.pk]), {"enabled":"truthy"})
        self.assertEqual(resp.status_code,403)
        self.assertFalse(AIProviderConfig.objects.get(pk=self.provider.pk).enabled)
