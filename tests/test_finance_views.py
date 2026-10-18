# SPDX-License-Identifier: GPL-3.0-only
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.core.permissions import (
    get_accessible_profiles, get_editable_profiles, user_can_edit_profile, user_can_view_profile,
)
from apps.finance.models import BankAccount, FinancialProfile, ProfileGrant, Workspace, WorkspaceMembership


class FinanceWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username="owner", password="test-password")
        cls.reader = get_user_model().objects.create_user(username="reader")
        cls.outsider = get_user_model().objects.create_user(username="outsider")
        cls.workspace = Workspace.objects.create(name="Casa", created_by=cls.owner)
        cls.other_workspace = Workspace.objects.create(name="Outro núcleo", created_by=cls.outsider)
        cls.admin = WorkspaceMembership.objects.create(
            workspace=cls.workspace, user=cls.owner, role="admin",
        )
        cls.member = WorkspaceMembership.objects.create(workspace=cls.workspace, user=cls.reader)
        cls.other_member = WorkspaceMembership.objects.create(
            workspace=cls.other_workspace, user=cls.outsider, role="admin",
        )
        cls.profile = FinancialProfile.objects.create(workspace=cls.workspace, name="Pessoal")
        cls.hidden = FinancialProfile.objects.create(workspace=cls.workspace, name="Privado")
        cls.foreign = FinancialProfile.objects.create(workspace=cls.other_workspace, name="Externo")
        ProfileGrant.objects.create(membership=cls.admin, profile=cls.profile, can_edit=True)
        cls.reader_grant = ProfileGrant.objects.create(membership=cls.member, profile=cls.profile)
        BankAccount.objects.create(profile=cls.hidden, name="Conta privada", balance=999)
        BankAccount.objects.create(profile=cls.foreign, name="Conta externa", balance=123)

    def setUp(self):
        self.client.force_login(self.owner)

    def url(self, name, pk=None):
        if name in {"profile-list", "profile-create"}:
            kwargs = {"workspace_id": pk or self.workspace.pk}
        else:
            kwargs = {"profile_id": pk or self.profile.pk}
        return reverse(f"finance:{name}", kwargs=kwargs)

    def test_login_to_profile_and_account_workflow(self):
        self.client.logout()
        response = self.client.post(reverse("login"), {
            "username": "owner", "password": "test-password",
        }, follow=True)
        self.assertContains(response, self.url("profile-list"))
        self.assertNotContains(response, "Outro núcleo")
        response = self.client.get(self.url("profile-list"))
        self.assertContains(response, self.url("profile-create"))
        response = self.client.post(self.url("profile-create"), {
            "name": " Família ", "emoji": "🏠", "monthly_income": "1234.56",
            "workspace": self.other_workspace.pk,
        })
        profile = FinancialProfile.objects.get(workspace=self.workspace, name="Família")
        self.assertRedirects(response, self.url("profile-detail", profile.pk))
        self.assertEqual(profile.monthly_income, Decimal("1234.56"))
        grant = ProfileGrant.objects.get(profile=profile)
        self.assertEqual(grant.membership, self.admin)
        self.assertTrue(grant.can_view and grant.can_edit)
        response = self.client.post(self.url("account-create", profile.pk), {
            "name": "Banco", "kind": "bank", "balance": "42.10",
            "profile": self.foreign.pk, "is_archived": "on",
        }, follow=True)
        self.assertContains(response, "Banco")
        self.assertContains(response, "42,10")
        account = profile.accounts.get()
        self.assertEqual(account.balance, Decimal("42.10"))
        self.assertFalse(account.is_archived)

    def test_profile_limit_includes_hidden_profiles(self):
        for index in range(3):
            FinancialProfile.objects.create(workspace=self.workspace, name=f"Hidden {index}")
        response = self.client.post(self.url("profile-create"), {"name": "Sexto"})
        self.assertContains(response, "Máximo de cinco perfis")
        self.assertEqual(self.workspace.profiles.count(), 5)
        self.assertFalse(ProfileGrant.objects.filter(profile__name="Sexto").exists())

    def test_can_create_fifth_profile(self):
        for index in range(2):
            FinancialProfile.objects.create(workspace=self.workspace, name=f"Hidden {index}")
        response = self.client.post(self.url("profile-create"), {"name": "Quinto"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.workspace.profiles.count(), 5)

    def test_anonymous_routes_require_login(self):
        self.client.logout()
        for name in ("profile-list", "profile-create", "profile-detail", "account-create"):
            for method in (self.client.get, self.client.post):
                with self.subTest(name=name, method=method):
                    response = method(self.url(name))
                    self.assertEqual(response.status_code, 302)
                    self.assertIn("/login/?next=", response.url)

    def test_common_without_grant_cannot_access_hidden_or_foreign_profiles(self):
        self.client.force_login(self.reader)
        response = self.client.get(self.url("profile-list"))
        self.assertContains(response, "Pessoal")
        self.assertNotContains(response, "Privado")
        self.assertNotContains(response, "Externo")
        for profile in (self.hidden, self.foreign):
            self.assertEqual(self.client.get(self.url("profile-detail", profile.pk)).status_code, 403)
            for method in (self.client.get, self.client.post):
                self.assertEqual(method(self.url("account-create", profile.pk), {
                    "name": "Forbidden", "kind": "bank",
                }).status_code, 403)
        self.assertFalse(BankAccount.objects.filter(name="Forbidden").exists())
        for name in ("profile-list", "profile-create"):
            self.assertEqual(self.client.get(self.url(name, self.other_workspace.pk)).status_code, 403)
        self.assertEqual(self.client.post(self.url("profile-create", self.other_workspace.pk), {
            "name": "Forbidden",
        }).status_code, 403)

    def test_reader_can_view_but_cannot_create(self):
        self.client.force_login(self.reader)
        response = self.client.get(self.url("profile-detail"))
        self.assertContains(response, "Nenhuma conta cadastrada")
        self.assertNotContains(response, "Nova conta")
        self.assertNotContains(response, "Conta privada")
        self.assertNotContains(response, "Conta externa")
        self.assertNotContains(self.client.get(self.url("profile-list")), "Novo perfil")
        for name in ("profile-create", "account-create"):
            self.assertEqual(self.client.get(self.url(name)).status_code, 403)
            self.assertEqual(self.client.post(self.url(name), {
                "name": "Forbidden", "kind": "bank",
            }).status_code, 403)

    def test_common_editor_can_create_account(self):
        self.reader_grant.can_edit = True
        self.reader_grant.save()
        self.client.force_login(self.reader)
        response = self.client.post(self.url("account-create"), {"name": "Carteira", "kind": "cash"})
        self.assertRedirects(response, self.url("profile-detail"))
        self.assertEqual(self.profile.accounts.get().kind, "cash")

    def test_cross_workspace_grant_is_ignored(self):
        ProfileGrant.objects.create(membership=self.admin, profile=self.foreign, can_edit=True)
        self.assertFalse(user_can_view_profile(self.owner, self.foreign.pk))
        self.assertFalse(user_can_edit_profile(self.owner, self.foreign.pk))
        self.assertNotIn(self.foreign, get_accessible_profiles(self.owner))
        self.assertNotIn(self.foreign, get_editable_profiles(self.owner))
        self.assertEqual(self.client.get(self.url("profile-detail", self.foreign.pk)).status_code, 403)
        self.assertEqual(self.client.post(self.url("account-create", self.foreign.pk), {
            "name": "Forbidden", "kind": "bank",
        }).status_code, 403)

    def test_duplicate_names_are_form_errors_and_scoped(self):
        response = self.client.post(self.url("profile-create"), {"name": " Pessoal "})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].non_field_errors())
        self.assertEqual(self.workspace.profiles.count(), 2)
        self.client.post(self.url("account-create"), {"name": "Banco", "kind": "bank"})
        response = self.client.post(self.url("account-create"), {"name": " Banco ", "kind": "cash"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].non_field_errors())
        self.assertEqual(self.profile.accounts.count(), 1)
        response = self.client.post(self.url("account-create"), {"name": "Conta privada", "kind": "bank"})
        self.assertEqual(response.status_code, 302)

    def test_invalid_fields_do_not_write(self):
        for value in ("-1", "1.001", "not-money", "10000000000000"):
            for route, field in (("profile-create", "monthly_income"), ("account-create", "balance")):
                response = self.client.post(self.url(route), {"name": "Invalid", "kind": "bank", field: value})
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context["form"].errors)
        for route in ("profile-create", "account-create"):
            response = self.client.post(self.url(route), {"name": "   ", "kind": "bank"})
            self.assertIn("name", response.context["form"].errors)
        response = self.client.post(self.url("account-create"), {"name": "Invalid", "kind": "invalid"})
        self.assertIn("kind", response.context["form"].errors)
        self.assertFalse(FinancialProfile.objects.filter(name="Invalid").exists())
        self.assertFalse(BankAccount.objects.filter(name="Invalid").exists())

    def test_zero_and_unknown_values_remain_distinct(self):
        for name, value in (("Unknown", ""), ("Zero", "0")):
            self.client.post(self.url("account-create"), {"name": name, "kind": "bank", "balance": value})
            self.client.post(self.url("profile-create"), {"name": name, "monthly_income": value})
        self.assertIsNone(self.profile.accounts.get(name="Unknown").balance)
        self.assertEqual(self.profile.accounts.get(name="Zero").balance, Decimal("0"))
        self.assertIsNone(self.workspace.profiles.get(name="Unknown").monthly_income)
        self.assertEqual(self.workspace.profiles.get(name="Zero").monthly_income, Decimal("0"))
        response = self.client.get(self.url("profile-detail"))
        self.assertContains(response, "Desconhecido")
        self.assertContains(response, "0,00")

    def test_csrf_and_method_restrictions(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        for route in ("profile-create", "account-create"):
            self.assertEqual(client.post(self.url(route), {"name": "Forbidden"}).status_code, 403)
            response = client.get(self.url(route))
            self.assertContains(response, "csrfmiddlewaretoken")
            self.assertEqual(self.client.put(self.url(route)).status_code, 405)
        for route in ("profile-list", "profile-detail"):
            self.assertEqual(self.client.post(self.url(route)).status_code, 405)
        self.assertEqual(self.workspace.profiles.count(), 2)
        self.assertEqual(self.profile.accounts.count(), 0)
