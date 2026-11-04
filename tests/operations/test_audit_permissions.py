# SPDX-License-Identifier: GPL-3.0-only
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection, connections
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from apps.core.permissions import user_can_view_profile
from apps.finance.models import FinancialProfile, ProfileGrant, Workspace, WorkspaceMembership
from apps.finance.services.profiles import create_financial_profile


class ProfileConcurrencyTests(TransactionTestCase):
    def test_five_profile_limit_serializes_on_postgresql(self):
        if connection.vendor != "postgresql":
            self.skipTest("Exige bloqueio real PostgreSQL")
        user = get_user_model().objects.create_user(username="concurrent")
        workspace = Workspace.objects.create(name="Concurrency", created_by=user)
        for i in range(4):
            create_financial_profile(workspace_id=workspace.pk, name=f"Profile {i}")
        barrier = Barrier(2)

        def create(index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                create_financial_profile(workspace_id=workspace.pk, name=f"Concurrent {index}")
                return "created"
            except ValidationError:
                return "limited"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(create, [1, 2]))
        self.assertCountEqual(results, ["created", "limited"])
        self.assertEqual(workspace.profiles.count(), 5)


class PermissionAuditTests(TestCase):
    def test_admin_policy_revocation_and_edit_implies_view(self):
        user = get_user_model().objects.create_user(username="member")
        ws = Workspace.objects.create(name="Núcleo", created_by=user)
        member = WorkspaceMembership.objects.create(workspace=ws, user=user, role="admin")
        profile = FinancialProfile.objects.create(workspace=ws, name="Profile")
        self.assertTrue(user_can_view_profile(user, profile.pk))
        member.role = "common"
        member.save()
        self.assertFalse(user_can_view_profile(user, profile.pk))
        grant = ProfileGrant.objects.create(membership=member, profile=profile, can_view=False, can_edit=True)
        self.assertTrue(user_can_view_profile(user, profile.pk))
        self.client.force_login(user)
        url = reverse("finance:profile-detail", args=[profile.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        grant.delete()
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_operator_cannot_bypass_financial_services_in_admin(self):
        user = get_user_model().objects.create_superuser(username="operator", password="test-only")
        self.client.force_login(user)
        self.assertEqual(self.client.post(reverse("admin:finance_financialprofile_add"), {}).status_code, 403)
        self.assertEqual(self.client.post(reverse("admin:finance_bankaccount_add"), {}).status_code, 403)
