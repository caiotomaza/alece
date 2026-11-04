# SPDX-License-Identifier: GPL-3.0-only
"""Entradas manipuladas não podem provocar HTTP 500 ou gravar lotes inválidos."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.finance.import_views import _collect_row_decisions
from apps.finance.models import FinancialProfile, ImportBatch, Workspace, WorkspaceMembership
from apps.finance.services.imports import stage_import


class DecisionParserTests(SimpleTestCase):
    def test_valid_decision_with_split(self):
        got = _collect_row_decisions({
            "row_4_action": "create_new", "row_4_adjusted_amount": "20.00",
            "row_4_split_19": "20.00",
        })
        self.assertEqual(got[0]["row_id"], 4)
        self.assertEqual(str(got[0]["splits"][19]), "20.00")

    def test_invalid_row_and_account_ids_rejected(self):
        for post in (
            {"row_x_action": "ignore"},
            {"row_0_action": "ignore"},
            {"row_1_action": "create_new", "row_1_split_bogus": "1"},
            {"row_1_action": "create_new", "row_1_split_0": "1"},
        ):
            with self.subTest(post=post), self.assertRaises(ValidationError):
                _collect_row_decisions(post)

    def test_non_finite_negative_and_non_numeric_values_rejected(self):
        for amount in ("nan", "Infinity", "-1", "0", "not-a-number"):
            with self.subTest(amount=amount), self.assertRaises(ValidationError):
                _collect_row_decisions({
                    "row_1_action": "create_new", "row_1_split_2": amount,
                })

    def test_malformed_adjusted_amount_and_period_are_rejected(self):
        for value in ("abc", "NaN", "Infinity", "0", "-20"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                _collect_row_decisions({"row_1_action": "create_new", "row_1_adjusted_amount": value})
        with self.assertRaises(ValidationError):
            _collect_row_decisions({"row_1_action": "create_new", "row_1_competence_month": "2026-13"})
        with self.assertRaises(ValidationError):
            _collect_row_decisions({"row_1_action": "link_existing", "row_1_target_batch_id": "invalido"})


class UploadInputStabilityTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="import-validation-admin")
        workspace = Workspace.objects.create(name="Importação isolada", created_by=user)
        WorkspaceMembership.objects.create(workspace=workspace, user=user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=workspace, name="Principal")
        self.client.force_login(user)


    def test_staging_in_archived_profile_is_forbidden_without_writes(self):
        self.profile.is_archived = True
        self.profile.save(update_fields=["is_archived"])
        with self.assertRaises(ValidationError):
            stage_import(
                actor=self.profile.workspace.created_by, profile_id=self.profile.pk,
                account_id=None, file_content=b"Data,Descricao,Valor\n15/01/2024,Mercado,-1.00",
                filename="extrato.csv",
            )
        self.assertFalse(ImportBatch.objects.exists())

    def test_invalid_account_id_does_not_create_batch_or_http_500(self):
        result = self.client.post(reverse("finance:import-upload", args=[self.profile.pk]), {
            "account_id": "nao-e-numero",
            "file": SimpleUploadedFile(
                "teste.csv", b"Data,Descricao,Valor\n15/01/2024,Mercado,-1.00",
                content_type="text/csv",
            ),
        })
        self.assertEqual(result.status_code, 200)
        self.assertFalse(ImportBatch.objects.exists())
