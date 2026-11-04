# SPDX-License-Identifier: GPL-3.0-only
"""Execute em Postgres de teste, nunca no banco de produção."""
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.test import TestCase
from django.urls import reverse

from apps.core.session_security import revoke_db_sessions_for_user
from apps.finance.models import Workspace, WorkspaceMembership


class SecuritySessionRevocationTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.admin = users.objects.create_user(username="security-admin", password="StrongPassword123!")
        self.target = users.objects.create_user(username="security-target", password="StrongPassword123!")
        self.other = users.objects.create_user(username="security-other", password="StrongPassword123!")
        self.ws = Workspace.objects.create(name="Security A", created_by=self.admin)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.admin, role="admin")
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.target, role="common")
        self.client.force_login(self.admin)

    def _session(self, user):
        store = SessionStore()
        store["_auth_user_id"] = str(user.pk)
        store["_auth_user_backend"] = "django.contrib.auth.backends.ModelBackend"
        store.save()
        return store.session_key

    def test_revokes_real_signed_sessions_and_keeps_others(self):
        target_key = self._session(self.target)
        other_key = self._session(self.other)
        result = self.client.post(reverse("core:user-revoke-sessions", args=[self.ws.pk, self.target.pk]))
        self.assertEqual(result.status_code, 302)
        self.assertFalse(Session.objects.filter(session_key=target_key).exists())
        self.assertTrue(Session.objects.filter(session_key=other_key).exists())

    def test_revoke_helper_ignores_malformed_sessions_and_exact_user_id(self):
        other_key = self._session(self.other)
        target_key = self._session(self.target)
        Session.objects.create(session_key="malformed-session", session_data="not-a-django-session", expire_date=Session.objects.get(session_key=target_key).expire_date)
        self.assertEqual(revoke_db_sessions_for_user(self.target.pk), 1)
        self.assertTrue(Session.objects.filter(session_key="malformed-session").exists())
        self.assertTrue(Session.objects.filter(session_key=other_key).exists())

    def test_admin_password_reset_invalidates_target_session(self):
        key = self._session(self.target)
        response = self.client.post(reverse("core:user-password-reset", args=[self.ws.pk, self.target.pk]), {
            "new_password1": "OtherStrong123!", "new_password2": "OtherStrong123!",
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Session.objects.filter(session_key=key).exists())
        self.target.refresh_from_db()
        self.assertTrue(self.target.check_password("OtherStrong123!"))

    def test_admin_cannot_reset_password_of_user_in_multiple_workspaces(self):
        ws_b = Workspace.objects.create(name="Security B", created_by=self.other)
        WorkspaceMembership.objects.create(workspace=ws_b, user=self.target, role="common")
        url = reverse("core:user-password-reset", args=[self.ws.pk, self.target.pk])
        response = self.client.post(url, {"new_password1": "OtherStrong123!", "new_password2": "OtherStrong123!"})
        self.assertEqual(response.status_code, 403)
        self.target.refresh_from_db()
        self.assertTrue(self.target.check_password("StrongPassword123!"))
        self.assertEqual(self.client.post(reverse("core:user-revoke-sessions", args=[self.ws.pk, self.target.pk])).status_code, 403)

    def test_local_admin_cannot_reset_global_superuser_password(self):
        self.target.is_superuser = True
        self.target.save(update_fields=["is_superuser"])
        response = self.client.post(reverse("core:user-password-reset", args=[self.ws.pk, self.target.pk]), {
            "new_password1": "OtherStrong123!", "new_password2": "OtherStrong123!",
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.post(reverse("core:user-revoke-sessions", args=[self.ws.pk, self.target.pk])).status_code, 403)
        self.target.refresh_from_db()
        self.assertTrue(self.target.check_password("StrongPassword123!"))

    def test_anonymous_user_cannot_revoke(self):
        self.client.logout()
        resp = self.client.post(reverse("core:user-revoke-sessions", args=[self.ws.pk, self.target.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/entrar/", resp.url)

    def test_non_admin_cannot_revoke(self):
        self.client.force_login(self.target)
        resp = self.client.post(reverse("core:user-revoke-sessions", args=[self.ws.pk, self.admin.pk]))
        self.assertEqual(resp.status_code, 403)
