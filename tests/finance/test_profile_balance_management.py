# SPDX-License-Identifier: GPL-3.0-only
"""Contas do perfil: identidade, saldos, permissões e retorno contextual."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.finance.models import BankAccount, FinancialProfile, ProfileGrant, Workspace, WorkspaceMembership


class ProfileBalancesManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(username="balance-admin")
        cls.reader = get_user_model().objects.create_user(username="balance-reader")
        cls.workspace = Workspace.objects.create(name="Núcleo de teste", created_by=cls.admin)
        WorkspaceMembership.objects.create(workspace=cls.workspace, user=cls.admin, role="admin")
        membership = WorkspaceMembership.objects.create(workspace=cls.workspace, user=cls.reader)
        cls.profile = FinancialProfile.objects.create(workspace=cls.workspace, name="Principal")
        cls.other = FinancialProfile.objects.create(workspace=cls.workspace, name="Privado")
        cls.grant = ProfileGrant.objects.create(
            profile=cls.profile, membership=membership,
            can_view=True, accounts_level="view",
        )
        cls.bank = BankAccount.objects.create(
            profile=cls.profile, name="Inter", kind="bank", balance=Decimal("825.40"),
        )
        cls.cash = BankAccount.objects.create(
            profile=cls.profile, name="Carteira", kind="cash", balance=Decimal("0.00"),
        )
        BankAccount.objects.create(profile=cls.profile, name="Caixa desconhecida", kind="bank")
        BankAccount.objects.create(profile=cls.other, name="Conta sigilosa", balance=999)

    def setUp(self):
        self.client.force_login(self.admin)
        self.url = reverse("finance:profile-detail", args=[self.profile.pk])

    def test_accounts_list_name_profile_amount_and_kind(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for value in ("Nome", "Perfil financeiro", "Quantia", "Inter", "Carteira",
                      "Conta bancária", "Dinheiro físico", "Desconhecida", "0,00"):
            self.assertContains(response, value)
        self.assertNotContains(response, "Conta sigilosa")
        self.assertContains(response, "balances-new-account")
        self.assertContains(response, "?return=profile")

    def test_view_only_cannot_edit_or_create(self):
        self.client.force_login(self.reader)
        response = self.client.get(self.url)
        self.assertContains(response, "Inter")
        self.assertNotContains(response, "Nova conta")
        self.assertNotContains(response, "Editar conta Inter")
        self.assertEqual(self.client.post(
            reverse("finance:account-create", args=[self.profile.pk]) + "?return=profile",
            {"name": "Sem acesso", "kind": "bank", "balance": "10.00"},
        ).status_code, 403)
        self.assertFalse(BankAccount.objects.filter(name="Sem acesso").exists())

    def test_profile_access_without_accounts_grant_does_not_expose_balances(self):
        self.grant.accounts_level = "none"
        self.grant.overview_level = "view"
        self.grant.save(update_fields=["accounts_level", "overview_level"])
        self.client.force_login(self.reader)
        response = self.client.get(self.url)
        self.assertContains(response, "Acesso restrito a contas e saldos")
        self.assertNotContains(response, "Inter")
        self.assertNotContains(response, "825,40")
        self.assertNotContains(response, "Nova conta")

    def test_create_and_edit_return_to_profile_only_when_requested(self):
        create_url = reverse("finance:account-create", args=[self.profile.pk])
        response = self.client.get(create_url + "?return=profile")
        self.assertEqual(response.context["cancel_url"], self.url)
        response = self.client.post(create_url + "?return=profile", {
            "name": "Itaú", "kind": "bank", "balance": "150.00",
        })
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        account = BankAccount.objects.get(profile=self.profile, name="Itaú")
        edit_url = reverse("finance:account-edit", args=[self.profile.pk, account.pk])
        edit_response = self.client.get(edit_url + "?return=profile")
        self.assertEqual(edit_response.context["cancel_url"], self.url)
        result = self.client.post(edit_url + "?return=profile", {
            "name": "Itaú", "kind": "bank", "balance": "200.00",
        })
        self.assertRedirects(result, self.url, fetch_redirect_response=False)
        account.refresh_from_db()
        self.assertEqual(account.balance, Decimal("200.00"))

    def test_contextless_create_still_returns_to_overview(self):
        create_url = reverse("finance:account-create", args=[self.profile.pk])
        response = self.client.get(create_url)
        self.assertEqual(response.context["cancel_url"], reverse("visao-geral"))

    def test_foreign_profile_account_never_accessible(self):
        self.client.force_login(self.reader)
        self.assertEqual(self.client.get(reverse(
            "finance:profile-detail", args=[self.other.pk],
        )).status_code, 403)
        self.assertEqual(self.client.get(reverse(
            "finance:account-edit", args=[self.other.pk, self.bank.pk],
        )).status_code, 403)
