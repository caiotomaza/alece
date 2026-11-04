# SPDX-License-Identifier: GPL-3.0-only
"""Security and concurrency cases identified by the independent audit."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import DatabaseError, connections, transaction
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from apps.core.models import SystemLog
from apps.finance.management.commands.verify_ledger_backup import Command as VerifyLedgerCommand
from apps.finance.models import (
    BankAccount, FinancialProfile, UnexpectedExpense, Workspace, WorkspaceMembership,
)
from apps.finance.services.imports import stage_import
from apps.finance.services.records import save_record
from apps.finance.services.system_log import log_error_event


class FirstRunBoundaryTests(TransactionTestCase):
    @override_settings(ALECE_BIND_IP="0.0.0.0")
    def test_public_binding_blocks_setup_even_with_forged_private_headers(self):
        response = self.client.post(
            reverse("setup"),
            {"username": "first", "password1": "StrongPass123", "password2": "StrongPass123"},
            HTTP_X_FORWARDED_FOR="127.0.0.1", REMOTE_ADDR="172.18.0.1",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(get_user_model().objects.exists())
        self.assertEqual(self.client.get(reverse("home")).status_code, 503)

    def test_two_setup_requests_create_exactly_one_administrator(self):
        barrier = Barrier(2)

        def submit(index):
            client = Client()
            barrier.wait(timeout=5)
            try:
                return client.post(reverse("setup"), {
                    "username": f"first{index}", "password1": "StrongPass123",
                    "password2": "StrongPass123",
                }).status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(submit, range(2)))
        self.assertEqual(statuses, [302, 302])
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(Workspace.objects.count(), 1)
        self.assertEqual(WorkspaceMembership.objects.filter(role="admin").count(), 1)


class SystemLogBoundaryTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username="audit-admin", password="StrongPass123")
        self.common = User.objects.create_user(username="audit-common", password="StrongPass123")
        self.other_admin = User.objects.create_user(username="audit-other", password="StrongPass123")
        self.workspace = Workspace.objects.create(name="Audit A", created_by=self.admin)
        self.other_workspace = Workspace.objects.create(name="Audit B", created_by=self.other_admin)
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.admin, role="admin")
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.common, role="common")
        WorkspaceMembership.objects.create(
            workspace=self.other_workspace, user=self.other_admin, role="admin",
        )
        self.own_log = SystemLog.objects.create(
            module="system", action="create", result="success", description="own",
            workspace=self.workspace, user=self.admin,
        )
        self.other_log = SystemLog.objects.create(
            module="system", action="create", result="success", description="other",
            workspace=self.other_workspace, user=self.other_admin,
        )

    def test_administrator_scope_and_common_denial(self):
        self.client.force_login(self.admin)
        list_response = self.client.get(reverse("logs"))
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "own")
        self.assertNotContains(list_response, "other")
        self.assertEqual(
            self.client.get(reverse("logs") + f"?abrir={self.other_log.pk}").status_code,
            404,
        )
        self.client.force_login(self.common)
        self.assertEqual(self.client.get(reverse("logs")).status_code, 403)
        self.assertEqual(
            self.client.get(reverse("logs") + f"?abrir={self.own_log.pk}").status_code,
            403,
        )

    def test_logs_are_immutable_and_error_payload_is_sanitized(self):
        request = self.client.request().wsgi_request
        request.META["REMOTE_ADDR"] = "127.0.0.1"
        request.META["HTTP_X_FORWARDED_FOR"] = "8.8.8.8"
        event = log_error_event(
            module="auth", action="login", description="password=private",
            error_message="token=private", exception=ValueError("secret"),
            request=request, details={"account_number": "private"},
        )
        self.assertNotIn("private", event.description + str(event.details))
        self.assertEqual(str(event.ip_address), "127.0.0.1")
        with self.assertRaises(DatabaseError), transaction.atomic():
            SystemLog.objects.filter(pk=event.pk).update(description="changed")
        with self.assertRaises(DatabaseError), transaction.atomic():
            SystemLog.objects.filter(pk=event.pk).delete()


class ImportIsolationTests(TestCase):
    def test_same_statement_in_two_profiles_has_distinct_row_keys(self):
        user = get_user_model().objects.create_user(username="import-audit")
        profiles = []
        for index in range(2):
            workspace = Workspace.objects.create(name=f"Núcleo {index}", created_by=user)
            WorkspaceMembership.objects.create(workspace=workspace, user=user, role="admin")
            profiles.append(FinancialProfile.objects.create(workspace=workspace, name="Principal"))

        content = b"Data,Descricao,Valor\n23/10/2026,Compra de teste,-12.00"
        batches = [stage_import(
            actor=user, profile_id=profile.pk, account_id=None,
            file_content=content, filename="sintetico.csv",
        ) for profile in profiles]
        self.assertNotEqual(batches[0].rows.get().idempotency_key,
                            batches[1].rows.get().idempotency_key)


class RegistrationAuditTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="record-audit")
        self.workspace = Workspace.objects.create(name="Audit", created_by=self.user)
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.user, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.workspace, name="Principal")

    def test_registration_and_log_commit_together(self):
        data = {"name": "Despesa sintética", "amount": Decimal("12.34")}
        with patch("apps.finance.services.records.log_financial_operation", side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                save_record(self.user, self.profile.pk, UnexpectedExpense, data)
        self.assertFalse(UnexpectedExpense.objects.exists())

        obj = save_record(self.user, self.profile.pk, UnexpectedExpense, data)
        event = SystemLog.objects.get(object_type="UnexpectedExpense", object_id=str(obj.pk))
        self.assertEqual(event.workspace_id, self.workspace.pk)
        self.assertNotIn("Despesa sintética", event.description + str(event.details))

    def test_backup_snapshot_preserves_unknown_balance(self):
        BankAccount.objects.create(
            profile=self.profile, name="Conta sem saldo", balance=None, opening_balance=None,
        )
        snapshot = VerifyLedgerCommand()._generate_snapshot(self.profile)
        account = snapshot["accounts"][0]
        self.assertIsNone(account["opening_balance"])
        self.assertIsNone(account["current_balance"])
        self.assertIsNone(account["calculated_balance"])
        self.assertIsNone(account["reconciled"])
