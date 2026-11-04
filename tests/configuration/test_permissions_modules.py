# SPDX-License-Identifier: GPL-3.0-only
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.core.permissions import get_module_profiles, user_can_module
from apps.finance.models import (
    BankAccount, FinancialProfile, ProfileGrant, RecurringExpense,
    Workspace, WorkspaceMembership,
)
from apps.finance.services.grants import GRANT_FIELDS, save_grant
from apps.finance.services.records import save_record


class GranularPermissionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username="p-admin")
        self.common = User.objects.create_user(username="p-common")
        self.foreign = User.objects.create_user(username="p-foreign")
        self.workspace = Workspace.objects.create(name="Primeiro", created_by=self.admin)
        self.other_workspace = Workspace.objects.create(name="Segundo", created_by=self.foreign)
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.admin, role="admin")
        self.member = WorkspaceMembership.objects.create(
            workspace=self.workspace, user=self.common, role="common",
        )
        self.foreign_member = WorkspaceMembership.objects.create(
            workspace=self.other_workspace, user=self.foreign, role="admin",
        )
        self.profile = FinancialProfile.objects.create(
            workspace=self.workspace, name="Visível", monthly_income=Decimal("321.00"),
        )
        self.hidden = FinancialProfile.objects.create(workspace=self.workspace, name="Privado")
        self.outside = FinancialProfile.objects.create(workspace=self.other_workspace, name="Fora")
        BankAccount.objects.create(
            profile=self.profile, name="Saldo sigiloso", balance=Decimal("77"),
            opening_balance=Decimal("77"),
        )
        RecurringExpense.objects.create(
            profile=self.profile, name="Despesa autorizada", category="essential",
            amount=Decimal("10"), due_day=1,
        )

    def levels(self, **overrides):
        return {field: overrides.get(field, "none") for field in GRANT_FIELDS}

    def test_default_none_admin_scope_and_module_independence(self):
        self.assertTrue(user_can_module(self.admin, self.profile.pk, "investments", "edit"))
        self.assertFalse(user_can_module(self.admin, self.outside.pk, "overview"))
        self.assertFalse(user_can_module(self.common, self.profile.pk, "expenses"))
        grant = save_grant(
            actor=self.admin, profile_id=self.profile.pk, membership_id=self.member.pk,
            levels=self.levels(overview_level="view", expenses_level="edit"),
        )
        self.assertTrue(grant.can_view and grant.can_edit)
        self.assertTrue(user_can_module(self.common, self.profile.pk, "expenses", "view"))
        self.assertTrue(user_can_module(self.common, self.profile.pk, "expenses", "edit"))
        self.assertFalse(user_can_module(self.common, self.profile.pk, "investments"))
        self.assertEqual(list(get_module_profiles(self.common, "expenses")), [self.profile])
        self.assertNotIn(self.hidden, get_module_profiles(self.common, "expenses"))
        with self.assertRaises(PermissionDenied):
            save_record(self.common, self.profile.pk, BankAccount, {"name": "Negada"})
        save_record(self.common, self.profile.pk, RecurringExpense, {
            "name": "Permitida", "category": "essential", "amount": Decimal("1"), "due_day": 1,
        })

    def test_revocation_on_next_request_and_no_cross_workspace_grant(self):
        save_grant(
            actor=self.admin, profile_id=self.profile.pk, membership_id=self.member.pk,
            levels=self.levels(overview_level="view", expenses_level="view"),
        )
        self.client.force_login(self.common)
        url = reverse("finance:expenses", args=[self.workspace.pk])
        self.assertContains(self.client.get(url), "Despesa autorizada")
        save_grant(
            actor=self.admin, profile_id=self.profile.pk, membership_id=self.member.pk,
            levels=self.levels(),
        )
        self.assertNotContains(self.client.get(url), "Despesa autorizada")
        self.assertEqual(self.client.get(reverse("finance:profile-detail", args=[self.profile.pk])).status_code, 403)
        with self.assertRaises(ValidationError):
            save_grant(
                actor=self.admin, profile_id=self.profile.pk,
                membership_id=self.foreign_member.pk,
                levels=self.levels(expenses_level="edit"),
            )
        self.assertFalse(ProfileGrant.objects.filter(profile=self.outside, membership=self.member).exists())

    def test_overview_does_not_expose_denied_account_or_expense_data(self):
        save_grant(
            actor=self.admin, profile_id=self.profile.pk, membership_id=self.member.pk,
            levels=self.levels(overview_level="view"),
        )
        self.client.force_login(self.common)
        overview = self.client.get(reverse("finance:overview", args=[self.workspace.pk]))
        self.assertContains(overview, "321,00")
        self.assertNotContains(overview, "Saldo sigiloso")
        self.assertNotContains(overview, "Despesa autorizada")
        self.assertNotContains(overview, "77,00")
        self.assertNotContains(overview, "Privado")
        self.assertEqual(self.client.get(reverse("finance:expenses", args=[self.workspace.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("finance:account-edit", args=[self.profile.pk, 1])).status_code, 403)

    def test_grant_ui_is_administrator_only_and_profile_scoped(self):
        self.client.force_login(self.admin)
        url = reverse("finance:grant-edit", args=[self.profile.pk, self.member.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.post(url, self.levels(accounts_level="view", movements_level="edit"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(user_can_module(self.common, self.profile.pk, "movements", "edit"))
        self.client.force_login(self.common)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, self.levels(expenses_level="edit")).status_code, 403)
