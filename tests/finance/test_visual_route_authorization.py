# SPDX-License-Identifier: GPL-3.0-only
"""The visual destinations must retain object authorization on their real links."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.finance.models import (
    FinancialProfile, ImportBatch, ProfileGrant, Workspace, WorkspaceMembership,
)
from apps.finance.services.reports import (
    InvestmentReport, export_investment_csv,
)


class ListingScopeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.admin = users.objects.create_user(username="listing-admin")
        cls.reader = users.objects.create_user(username="listing-reader")
        cls.workspace = Workspace.objects.create(name="Synthetic", created_by=cls.admin)
        WorkspaceMembership.objects.create(
            workspace=cls.workspace, user=cls.admin, role="admin",
        )
        membership = WorkspaceMembership.objects.create(
            workspace=cls.workspace, user=cls.reader, role="common",
        )
        cls.allowed = FinancialProfile.objects.create(workspace=cls.workspace, name="Allowed")
        cls.hidden = FinancialProfile.objects.create(workspace=cls.workspace, name="Hidden")
        cls.grant = ProfileGrant.objects.create(
            membership=membership, profile=cls.allowed,
            accounts_level="view", movements_level="view",
            overview_level="view", expenses_level="view", investments_level="view",
        )
        for profile, name in ((cls.allowed, "allowed.csv"), (cls.hidden, "hidden.csv")):
            ImportBatch.objects.create(
                profile=profile, filename=name, file_hash="0" * 64,
                format="csv", parser_version="test", created_by=cls.admin,
            )

    def test_import_listing_and_filter_are_scoped_to_each_granted_profile(self):
        self.client.force_login(self.reader)
        url = reverse("finance:import-list", args=[self.workspace.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "allowed.csv")
        self.assertNotContains(response, "hidden.csv")
        self.assertNotContains(response, "Hidden")
        self.assertEqual(self.client.get(url, {"profile": self.hidden.pk}).status_code, 404)
        self.assertEqual(self.client.get(url, {"profile": "invalid"}).status_code, 404)
        self.grant.accounts_level = "none"
        self.grant.save(update_fields=["accounts_level"])
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_report_listing_selection_and_detail_are_scoped(self):
        self.client.force_login(self.reader)
        dashboard = reverse("finance:reports-dashboard", args=[self.workspace.pk])
        response = self.client.get(dashboard)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Hidden")
        self.assertEqual(self.client.get(dashboard, {"profile": self.hidden.pk}).status_code, 404)
        detail = reverse("finance:investment-report", args=[self.workspace.pk, self.allowed.pk])
        self.assertEqual(self.client.get(detail).status_code, 200)
        hidden_detail = reverse("finance:investment-report", args=[self.workspace.pk, self.hidden.pk])
        self.assertEqual(self.client.get(hidden_detail).status_code, 403)
        self.grant.investments_level = "none"
        self.grant.save(update_fields=["investments_level"])
        self.assertEqual(self.client.get(dashboard).status_code, 403)

    def test_csv_export_is_csv_and_neutralizes_spreadsheet_formulas(self):
        report = InvestmentReport(profile="Synthetic", as_of=self.allowed.created_at.date())
        report.positions.append({
            "name": "=cmd", "institution": "@bank", "category": "Reserva",
            "applied_amount": Decimal("10.00"), "current_value": Decimal("11.00"),
            "target_amount": None,
        })
        report.positions.append({
            "name": "Zero target", "institution": "Bank", "category": "Reserva",
            "applied_amount": Decimal("0.00"), "current_value": Decimal("0.00"),
            "target_amount": Decimal("0.00"),
        })
        data = export_investment_csv(report).decode("utf-8-sig")
        self.assertIn("Posição;Instituição;Categoria;Aplicado;Atual;Meta", data)
        self.assertIn("'=cmd;'@bank;Reserva;10.00;11.00", data)
        self.assertIn("Zero target;Bank;Reserva;0.00;0.00;0.00", data)

    def test_movement_upload_uses_only_editable_selected_profile(self):
        self.client.force_login(self.reader)
        url = reverse("finance:movements", args=[self.workspace.pk])
        response = self.client.get(url, {"profiles": self.allowed.pk})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="file"')
        self.grant.accounts_level = "edit"
        self.grant.movements_level = "edit"
        self.grant.save(update_fields=["accounts_level", "movements_level"])
        response = self.client.get(url, {"profiles": self.allowed.pk})
        self.assertEqual(response.status_code, 200)
        upload = reverse("finance:import-upload", args=[self.allowed.pk])
        self.assertContains(response, f'action="{upload}"')
        self.assertNotContains(response, "hidden.csv")
        self.grant.movements_level = "view"
        self.grant.save(update_fields=["movements_level"])
        self.assertNotContains(self.client.get(url, {"profiles": self.allowed.pk}), 'name="file"')
