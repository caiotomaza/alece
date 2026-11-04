# SPDX-License-Identifier: GPL-3.0-only
"""HTTP authorization matrix: fake accounts and one isolated workspace only."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from apps.finance.models import FinancialProfile, Workspace, WorkspaceMembership


class AdministrativeAccessMatrixTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user=get_user_model()
        cls.admin=user.objects.create_user(username="matrix-admin",password="Unreal12345!")
        cls.common=user.objects.create_user(username="matrix-common",password="Unreal12345!")
        cls.foreign=user.objects.create_user(username="matrix-foreign",password="Unreal12345!")
        cls.workspace=Workspace.objects.create(name="Matriz de permissões",created_by=cls.admin)
        cls.other=Workspace.objects.create(name="Outro tenant",created_by=cls.foreign)
        WorkspaceMembership.objects.create(workspace=cls.workspace,user=cls.admin,role="admin")
        WorkspaceMembership.objects.create(workspace=cls.workspace,user=cls.common,role="common")
        WorkspaceMembership.objects.create(workspace=cls.other,user=cls.foreign,role="admin")
        cls.profile=FinancialProfile.objects.create(workspace=cls.workspace,name="Principal")
        cls.foreign_profile=FinancialProfile.objects.create(workspace=cls.other,name="Principal externo")

    def test_all_administrative_pages_render_for_workspace_admin(self):
        self.client.force_login(self.admin)
        for route in ("configuracoes-usuarios","configuracoes-perfis","configuracoes-apis","logs","relatorios"):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(reverse(route)).status_code,200)

    def test_all_administrative_pages_deny_common_account(self):
        self.client.force_login(self.common)
        for route in ("configuracoes-usuarios","configuracoes-perfis","configuracoes-apis","logs","relatorios"):
            with self.subTest(route=route):
                self.assertEqual(self.client.get(reverse(route)).status_code,403)

    def test_common_account_can_access_personal_settings(self):
        self.client.force_login(self.common)
        response=self.client.get(reverse("configuracoes"))
        self.assertEqual(response.status_code,200)
        self.assertNotContains(response,"Gerenciar usuários")

    def test_foreign_workspace_cannot_be_selected(self):
        self.client.force_login(self.admin)
        response=self.client.get(reverse("selecionar-nucleo",args=[self.other.pk]))
        self.assertEqual(response.status_code,403)
        response=self.client.get(reverse("finance:profile-manage",args=[self.foreign_profile.pk]))
        self.assertEqual(response.status_code,403)
