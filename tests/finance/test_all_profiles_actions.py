# SPDX-License-Identifier: GPL-3.0-only
"""Fluxos de criação e seleção explícita sem contaminar preferência da navegação."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.finance.models import (
    BankAccount, FinancialProfile, InvestmentPosition, ProfileGrant, RecurringExpense,
    TransactionBatch, UnexpectedExpense, Workspace, WorkspaceMembership,
)
from apps.finance.profile_selection import SESSION_KEY


class AllProfilesActionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(username="all-admin", password="OnlyTesting123!")
        cls.common = get_user_model().objects.create_user(username="all-common", password="OnlyTesting123!")
        cls.workspace = Workspace.objects.create(name="Familia", created_by=cls.admin)
        WorkspaceMembership.objects.create(workspace=cls.workspace, user=cls.admin, role=WorkspaceMembership.Role.ADMIN)
        cls.member = WorkspaceMembership.objects.create(
            workspace=cls.workspace, user=cls.common, role=WorkspaceMembership.Role.COMMON,
        )
        cls.principal = FinancialProfile.objects.create(workspace=cls.workspace, name="Principal")
        cls.secundario = FinancialProfile.objects.create(workspace=cls.workspace, name="Secundario")
        ProfileGrant.objects.create(
            profile=cls.principal, membership=cls.member,
            can_view=True, can_edit=True, expenses_level=ProfileGrant.Level.EDIT,
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def chooser(self, operation):
        return reverse("finance:choose-profile-action", args=[self.workspace.pk, operation])

    def test_all_displays_create_and_income_buttons_even_with_multiple_profiles(self):
        self.client.get(reverse("despesas") + "?profiles=all")
        resp = self.client.get(reverse("despesas"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.chooser("recurring"))
        self.assertContains(resp, self.chooser("unexpected"))
        self.assertNotIn(SESSION_KEY, self.client.session)
        overview = self.client.get(reverse("visao-geral"))
        self.assertContains(overview, self.chooser("account"))
        self.assertContains(overview, reverse("finance:income-bulk", args=[self.workspace.pk]))
        investment = self.client.get(reverse("investimentos"))
        self.assertContains(investment, self.chooser("investment"))
        movements = self.client.get(reverse("movimentacoes"))
        self.assertContains(movements, self.chooser("transfer"))

    def test_creation_form_opens_directly_with_profile_dropdown(self):
        for operation, field in (
            ("recurring", "due_day"), ("unexpected", "amount"),
            ("investment", "applied_amount"), ("account", "balance"),
            ("transfer", "source"),
        ):
            with self.subTest(operation=operation):
                response = self.client.get(self.chooser(operation))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateNotUsed(response, "finance/choose_profile.html")
                self.assertContains(response, 'name="profile_id"')
                self.assertContains(response, f'name="{field}"')
                self.assertContains(response, "Perfil financeiro")
                self.assertNotContains(response, "Selecione o perfil financeiro onde esta operação")
                choices = list(response.context["form"].fields["profile_id"].queryset)
                self.assertEqual([item.pk for item in choices], [self.principal.pk, self.secundario.pk])

    def test_selector_only_lists_editable_authorized_profiles(self):
        self.client.force_login(self.common)
        resp = self.client.get(self.chooser("recurring"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(list(resp.context["form"].fields["profile_id"].queryset), [self.principal])
        self.assertContains(resp, "Principal")
        self.assertNotContains(resp, "Secundario")
        self.assertEqual(self.client.get(self.chooser("unknown")).status_code, 404)
        for operation in ("account", "investment", "transfer"):
            self.assertEqual(self.client.get(self.chooser(operation)).status_code, 403)
        self.assertEqual(self.client.get(reverse("finance:recurring-create", args=[self.secundario.pk])).status_code, 403)

    def test_post_rejects_missing_invalid_and_foreign_profile_without_writing(self):
        payload = {"name": "Tentativa", "category": "essential", "amount": "24.00", "due_day": "8"}
        url = self.chooser("recurring")
        for candidate in ("", "invalid", "999999"):
            with self.subTest(candidate=candidate):
                response = self.client.post(url, {**payload, "profile_id": candidate})
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "Perfil financeiro")
                self.assertFalse(RecurringExpense.objects.filter(name="Tentativa").exists())
        self.client.force_login(self.common)
        response = self.client.post(url, {**payload, "profile_id": self.secundario.pk})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(RecurringExpense.objects.filter(name="Tentativa").exists())
        other = Workspace.objects.create(name="Núcleo externo", created_by=self.admin)
        foreign = FinancialProfile.objects.create(workspace=other, name="Outro núcleo")
        self.client.force_login(self.admin)
        response = self.client.post(url, {**payload, "profile_id": foreign.pk})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(RecurringExpense.objects.filter(name="Tentativa").exists())

    def test_account_and_unexpected_can_save_from_same_modal(self):
        account = self.client.post(self.chooser("account"), {
            "profile_id": self.secundario.pk, "name": "Carteira",
            "kind": "cash", "balance": "75.00",
        })
        self.assertRedirects(account, reverse("visao-geral"), fetch_redirect_response=False)
        self.assertTrue(BankAccount.objects.filter(profile=self.secundario, name="Carteira").exists())
        surprise = self.client.post(self.chooser("unexpected"), {
            "profile_id": self.principal.pk, "name": "Farmácia", "amount": "22.50",
        })
        self.assertRedirects(surprise, reverse("despesas"), fetch_redirect_response=False)
        self.assertTrue(UnexpectedExpense.objects.filter(profile=self.principal, name="Farmácia").exists())

    def test_explicit_profile_from_balances_page_is_preselected_but_editable(self):
        url = self.chooser("account") + f"?profile_id={self.principal.pk}&return=profile"
        response = self.client.get(url)
        self.assertEqual(response.context["form"].initial["profile_id"], self.principal.pk)
        self.assertContains(response, 'name="profile_id"')
        saved = self.client.post(url, {
            "profile_id": self.secundario.pk, "name": "Outra carteira",
            "kind": "cash", "balance": "4.00",
        })
        self.assertRedirects(saved, reverse("finance:profile-detail", args=[self.secundario.pk]),
                             fetch_redirect_response=False)
        self.assertTrue(BankAccount.objects.filter(profile=self.secundario, name="Outra carteira").exists())

    def test_transfer_stays_on_single_form_and_refreshes_account_options(self):
        bank = BankAccount.objects.create(profile=self.principal, name="Banco A", kind="bank",
                                          balance="100.00", opening_balance="100.00")
        cash = BankAccount.objects.create(profile=self.principal, name="Dinheiro", kind="cash",
                                          balance="20.00", opening_balance="20.00")
        response = self.client.get(self.chooser("transfer") + f"?profile_id={self.principal.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-profile-refresh="true"')
        self.assertContains(response, "Banco A")
        posted = self.client.post(self.chooser("transfer"), {
            "profile_id": self.principal.pk, "source": bank.pk, "destination": cash.pk,
            "amount": "10.00", "idempotency_key": "workspace-transfer-1", "note": "Teste",
        })
        self.assertRedirects(posted, reverse("movimentacoes"), fetch_redirect_response=False)
        self.assertEqual(TransactionBatch.objects.filter(profile=self.principal,
                         idempotency_key="workspace-transfer-1").count(), 1)


    def test_saving_when_all_does_not_select_written_profile(self):
        self.client.get(reverse("despesas") + "?profiles=all")
        self.assertEqual(self.client.get(self.chooser("recurring")).status_code, 200)
        response = self.client.post(self.chooser("recurring"), {
            "profile_id": self.principal.pk,
            "name": "Conta da casa", "category": "essential", "amount": "18.25", "due_day": "10",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("despesas"))
        self.assertTrue(RecurringExpense.objects.filter(profile=self.principal, name="Conta da casa").exists())
        self.assertNotIn(SESSION_KEY, self.client.session)
        listing = self.client.get(reverse("despesas"))
        self.assertEqual(len(listing.context["sections"]), 2)
        self.assertContains(listing, "Todos os perfis")

    def test_saving_keeps_current_selected_profile_even_if_record_belongs_to_other(self):
        self.client.get(reverse("despesas") + f"?profiles={self.secundario.pk}")
        result = self.client.post(self.chooser("recurring"), {
            "profile_id": self.principal.pk,
            "name": "Despesa de outro", "category": "essential", "amount": "15.00", "due_day": "5",
        })
        self.assertEqual(result.status_code, 302)
        self.assertEqual(self.client.session[SESSION_KEY]["profile_id"], self.secundario.pk)
        listing = self.client.get(reverse("despesas"))
        self.assertEqual([s["profile"].pk for s in listing.context["sections"]], [self.secundario.pk])

    def test_month_filter_does_not_write_profile_preference(self):
        self.client.get(reverse("despesas") + "?profiles=all")
        resp = self.client.get(reverse("despesas") + "?month=2026-10")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertNotContains(resp, 'type="hidden" name="profiles"')

    def test_edit_form_and_account_save_keep_sidebar_preference(self):
        self.client.get(reverse("visao-geral") + f"?profiles={self.secundario.pk}")
        editor = self.client.get(reverse("finance:income-edit", args=[self.principal.pk]))
        self.assertEqual(editor.status_code, 200)
        self.assertContains(editor, "Secundario")
        created = self.client.post(reverse("finance:account-create", args=[self.principal.pk]), {
            "name": "Conta do principal", "kind": "bank", "balance": "20.00",
        })
        self.assertEqual(created.status_code, 302)
        self.assertEqual(created.url, reverse("visao-geral"))
        self.assertEqual(self.client.session[SESSION_KEY]["profile_id"], self.secundario.pk)
        self.assertEqual([item["profile"].pk for item in
                          self.client.get(reverse("visao-geral")).context["sections"]],
                         [self.secundario.pk])

    def test_with_one_available_profile_all_still_means_all(self):
        self.secundario.is_archived = True
        self.secundario.save(update_fields=["is_archived"])
        resp = self.client.get(reverse("despesas") + "?profiles=all")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Todos os perfis")
        self.assertContains(resp, self.chooser("recurring"))

    def test_import_in_all_requires_explicit_profile_not_first_in_list(self):
        resp = self.client.get(reverse("movimentacoes") + "?profiles=all")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context["import_profile"])
        self.assertContains(resp, 'data-import-profile-choice')
        self.assertContains(resp, 'Selecione um perfil')
        self.assertContains(resp, reverse("finance:import-upload", args=[self.secundario.pk]))
