# SPDX-License-Identifier: GPL-3.0-only
"""Server-side regression for the consolidated income popup (PostgreSQL test DB)."""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.finance.models import (
    BankAccount, FinancialProfile, ProfileGrant, TransactionBatch, Workspace, WorkspaceMembership,
)


class IncomeBulkModalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(username="income-admin")
        cls.common = get_user_model().objects.create_user(username="income-common")
        cls.stranger = get_user_model().objects.create_user(username="income-stranger")
        cls.ws = Workspace.objects.create(name="Nucleo de teste", created_by=cls.admin)
        WorkspaceMembership.objects.create(workspace=cls.ws, user=cls.admin, role="admin")
        cls.member = WorkspaceMembership.objects.create(workspace=cls.ws, user=cls.common, role="common")
        cls.profile_a = FinancialProfile.objects.create(
            workspace=cls.ws, name="Principal", monthly_income=Decimal("1000.00"),
        )
        cls.profile_b = FinancialProfile.objects.create(
            workspace=cls.ws, name="Família", monthly_income=None,
        )
        ProfileGrant.objects.create(
            membership=cls.member, profile=cls.profile_a, can_view=True, can_edit=True,
            overview_level=ProfileGrant.Level.EDIT,
        )

    def setUp(self):
        self.client.force_login(self.admin)
        self.url = reverse("finance:income-bulk", args=[self.ws.pk])

    def data(self, first="1500.00", second="0"):
        return {
            "profile_ids": f"{self.profile_a.pk},{self.profile_b.pk}",
            f"income_{self.profile_a.pk}-monthly_income": first,
            f"income_{self.profile_b.pk}-monthly_income": second,
        }

    def test_overview_opens_direct_dialog_without_profile_picker(self):
        response = self.client.get(reverse("visao-geral"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="overview-income-dialog"')
        self.assertContains(response, 'data-income-dialog-trigger')
        self.assertContains(response, f'href="{self.url}"')
        self.assertContains(response, "Renda dos perfis financeiros")

    def test_fallback_get_and_single_atomic_post(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-income-bulk-form')
        self.assertContains(response, 'name="profile_ids"')
        balance = BankAccount.objects.create(profile=self.profile_a, name="Banco", balance=Decimal("22"))
        self.assertEqual(self.client.post(self.url, self.data()).status_code, 302)
        self.profile_a.refresh_from_db()
        self.profile_b.refresh_from_db()
        balance.refresh_from_db()
        self.assertEqual(self.profile_a.monthly_income, Decimal("1500"))
        self.assertEqual(self.profile_b.monthly_income, Decimal("0"))
        self.assertEqual(balance.balance, Decimal("22"))
        self.assertEqual(TransactionBatch.objects.count(), 0)

    def test_all_fields_validated_before_any_write(self):
        data = self.data(first="1700", second="-1")
        response = self.client.post(self.url, data, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 422)
        self.assertIn(f"income_{self.profile_b.pk}-monthly_income", response.json()["field_errors"])
        self.profile_a.refresh_from_db()
        self.assertEqual(self.profile_a.monthly_income, Decimal("1000"))

    def test_atomic_rollback_when_second_update_fails(self):
        from apps.finance.views import update_income as actual_update
        def fail_second(user, profile_id, amount):
            if profile_id == self.profile_b.pk:
                raise ValidationError("Falha sintética para verificar rollback")
            return actual_update(user, profile_id, amount)
        with patch("apps.finance.views.update_income", side_effect=fail_second):
            response = self.client.post(self.url, self.data(), HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 409)
        self.profile_a.refresh_from_db()
        self.assertEqual(self.profile_a.monthly_income, Decimal("1000"))

    def test_stale_and_missing_fields_rejected_without_writing(self):
        for data in (
            {**self.data(), "profile_ids": str(self.profile_a.pk)},
            {k: v for k, v in self.data().items() if k != f"income_{self.profile_b.pk}-monthly_income"},
        ):
            self.assertEqual(self.client.post(self.url, data).status_code, 409)
        self.profile_a.refresh_from_db()
        self.assertEqual(self.profile_a.monthly_income, Decimal("1000"))

    def test_common_may_edit_only_granted_profile(self):
        self.client.force_login(self.common)
        page = self.client.get(self.url)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Principal")
        self.assertNotContains(page, "Família")
        self.assertEqual(self.client.post(self.url, self.data()).status_code, 409)
        payload = {"profile_ids": str(self.profile_a.pk), f"income_{self.profile_a.pk}-monthly_income": "1250"}
        self.assertEqual(self.client.post(self.url, payload).status_code, 302)
        self.profile_a.refresh_from_db()
        self.profile_b.refresh_from_db()
        self.assertEqual(self.profile_a.monthly_income, Decimal("1250"))
        self.assertIsNone(self.profile_b.monthly_income)

    def test_no_access_denied(self):
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, self.data()).status_code, 403)
