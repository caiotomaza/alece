# SPDX-License-Identifier: GPL-3.0-only
"""Erros de importação não devolvem caminhos/segredos ao cliente."""
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.finance.models import Workspace, WorkspaceMembership


class ImportMessageMinimizationTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="import-security", password="StrongPassword123!")
        self.workspace = Workspace.objects.create(name="Import privacy", created_by=user)
        WorkspaceMembership.objects.create(workspace=self.workspace, user=user, role="admin")
        self.client.force_login(user)

    def test_operating_system_error_does_not_expose_internal_path(self):
        marker = "PRIVATE_PATH__BACKUP_CREDENTIAL"
        with patch("apps.finance.financial_transfer_views.parse_archive", side_effect=OSError(marker)):
            response = self.client.post(reverse("finance:financial-import", args=[self.workspace.pk]), {
                "archive": SimpleUploadedFile("financeiro.zip", b"synthetic-zip"),
                "confirm": "IMPORTAR", "grant_all": "yes",
            })
        self.assertEqual(response.status_code, 302)
        messages = " ".join(str(m) for m in get_messages(response.wsgi_request))
        self.assertNotIn(marker, messages)
        self.assertIn("não pôde ser processado", messages)

    def test_common_user_cannot_import(self):
        other = get_user_model().objects.create_user(username="import-common", password="StrongPassword123!")
        WorkspaceMembership.objects.create(workspace=self.workspace, user=other, role="common")
        self.client.force_login(other)
        response = self.client.post(reverse("finance:financial-import", args=[self.workspace.pk]), {
            "archive": SimpleUploadedFile("financeiro.zip", b"synthetic-zip"),
            "confirm": "IMPORTAR", "grant_all": "yes",
        })
        self.assertEqual(response.status_code, 403)
