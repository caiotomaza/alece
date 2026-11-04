# SPDX-License-Identifier: GPL-3.0-only
"""Regressão: salvar ou cancelar cadastro de saldo retorna à Visão geral.

Execute com PostgreSQL isolado: python manage.py test tests.finance.test_account_return_overview
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.finance.models import BankAccount, FinancialProfile, Workspace, WorkspaceMembership
from apps.finance.profile_selection import SESSION_KEY


class AccountReturnToOverviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="redirect-admin", password="TestPassword123!")
        cls.workspace = Workspace.objects.create(name="Teste de retorno", created_by=cls.user)
        WorkspaceMembership.objects.create(workspace=cls.workspace, user=cls.user, role=WorkspaceMembership.Role.ADMIN)
        cls.principal = FinancialProfile.objects.create(workspace=cls.workspace, name="Principal")
        cls.outro = FinancialProfile.objects.create(workspace=cls.workspace, name="Outro")

    def setUp(self):
        self.client.force_login(self.user)
        self.create_url = reverse("finance:account-create", args=[self.principal.pk])
        self.overview_url = reverse("visao-geral")

    def test_create_redirects_to_public_overview_not_legacy_profile(self):
        result = self.client.post(self.create_url, {
            "name": "Inter", "kind": "bank", "balance": "622.49",
        })
        self.assertRedirects(result, self.overview_url, fetch_redirect_response=False)
        self.assertNotIn("/financas/perfis/", result.url)
        self.assertEqual(BankAccount.objects.get(profile=self.principal).balance, Decimal("622.49"))
        response = self.client.get(result.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Visão geral")

    def test_cancel_link_returns_to_public_overview(self):
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["cancel_url"], self.overview_url)

    def test_account_creation_preserves_selected_profile(self):
        self.client.get(self.overview_url + f"?profiles={self.outro.pk}")
        self.assertEqual(self.client.session[SESSION_KEY]["profile_id"], self.outro.pk)
        result = self.client.post(self.create_url, {
            "name": "Carteira", "kind": "cash", "balance": "50.00",
        })
        self.assertRedirects(result, self.overview_url, fetch_redirect_response=False)
        self.assertEqual(self.client.session[SESSION_KEY]["profile_id"], self.outro.pk)
        self.assertEqual([item["profile"].pk for item in self.client.get(self.overview_url).context["sections"]], [self.outro.pk])

    def test_all_profiles_stays_all_after_create(self):
        self.client.get(self.overview_url + "?profiles=all")
        result = self.client.post(self.create_url, {
            "name": "Dinheiro", "kind": "cash", "balance": "10.00",
        })
        self.assertRedirects(result, self.overview_url, fetch_redirect_response=False)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertEqual(len(self.client.get(self.overview_url).context["sections"]), 2)

    def test_validation_error_does_not_create_account_or_redirect(self):
        result = self.client.post(self.create_url, {
            "name": "Inválida", "kind": "bank", "balance": "-1.00",
        })
        self.assertEqual(result.status_code, 200)
        self.assertFalse(BankAccount.objects.filter(profile=self.principal, name="Inválida").exists())
