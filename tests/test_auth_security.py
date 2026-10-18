# SPDX-License-Identifier: GPL-3.0-only
"""Security regression tests for public authentication and offline recovery."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connections
from django.test import Client, RequestFactory, TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone

from apps.core.auth_services import allow_auth_attempt, issue_recovery_code, redeem_recovery_code
from apps.core.auth_forms import ThrottledAdminAuthenticationForm
from apps.core.models import AuthenticationAttempt, UserProfile

User = get_user_model()


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AuthenticationSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="existing-password-42")
        self.data = {"username": self.user.username, "new_password1": "New-complex-password-42",
                     "new_password2": "New-complex-password-42"}

    def test_external_redirects_rejected_internal_allowed(self):
        for next_url in ["https://evil.example/", "//evil.example/", "http://testserver/"]:
            client = Client()
            response = client.post(reverse("login") + "?next=" + next_url,
                                   {"username": "owner", "password": "existing-password-42"}, secure=True)
            self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        response = Client().post(reverse("login") + "?next=/password/change/",
                                 {"username": "owner", "password": "existing-password-42"})
        self.assertRedirects(response, reverse("password_change"), fetch_redirect_response=False)

    def test_issuance_requires_login_and_current_password(self):
        response = self.client.post(reverse("recovery_generate"))
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.user)
        for password in ["", "wrong"]:
            self.client.post(reverse("recovery_generate"), {"current_password": password})
            self.assertFalse(UserProfile.objects.filter(user=self.user).exists())
        response = self.client.post(reverse("recovery_generate"), {"current_password": "existing-password-42"})
        code = response.context["code"]
        self.assertEqual(len(code), 32)
        self.assertNotEqual(self.user.profile.recovery_code_hash, code)
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertNotContains(self.client.get(reverse("recovery_generate")), code)

    def test_rotated_code_and_replayed_code_rejected(self):
        first = issue_recovery_code(self.user.pk, "existing-password-42")
        current = issue_recovery_code(self.user.pk, "existing-password-42")
        self.assertFalse(redeem_recovery_code("owner", first, self.data)[0])
        self.assertTrue(redeem_recovery_code("owner", current, self.data)[0])
        self.assertFalse(redeem_recovery_code("owner", current, self.data)[0])

    def test_legacy_publicly_issued_codes_are_rejected_after_upgrade(self):
        code = issue_recovery_code(self.user.pk, "existing-password-42")
        UserProfile.objects.filter(user=self.user).update(recovery_code_version=0)
        self.assertFalse(redeem_recovery_code("owner", code, self.data)[0])
        self.assertFalse(UserProfile.objects.get(user=self.user).has_recovery_code())

    def test_password_validation_preserves_code_until_valid_submission(self):
        code = issue_recovery_code(self.user.pk, "existing-password-42")
        for password in ["123", "password", "123456789012"]:
            success, _ = redeem_recovery_code("owner", code,
                                             {"new_password1": password, "new_password2": password})
            self.assertFalse(success)
            self.assertTrue(UserProfile.objects.get(user=self.user).verify_recovery_code(code))
        self.assertTrue(redeem_recovery_code("owner", code, self.data)[0])

    def test_invalid_recovery_is_generic_and_inactive_user_cannot_recover(self):
        code = issue_recovery_code(self.user.pk, "existing-password-42")
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        expected = ["Código de recuperação inválido."]
        for username, token in [("missing", code), ("owner", code), ("owner", "invalid")]:
            self.assertEqual(redeem_recovery_code(username, token, self.data), (False, expected))

    def test_login_throttled_across_clients_and_reopens_after_window(self):
        data = {"username": "owner", "password": "wrong"}
        for _ in range(10):
            self.assertEqual(Client().post(reverse("login"), data).status_code, 200)
        self.assertEqual(Client().post(reverse("login"), data).status_code, 429)
        for bucket in AuthenticationAttempt.objects.all():
            self.assertNotIn("owner", bucket.key)
            self.assertEqual(len(bucket.key), 64)
        AuthenticationAttempt.objects.update(window_started=timezone.now() - timedelta(minutes=16))
        self.assertEqual(Client().post(reverse("login"), data).status_code, 200)

    def test_admin_login_cannot_bypass_shared_limit_even_with_valid_password(self):
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        for _ in range(10):
            Client().post(reverse("login"), {"username": "owner", "password": "wrong"})
        request = RequestFactory().post("/admin/login/")
        form = ThrottledAdminAuthenticationForm(request, data={
            "username": "owner", "password": "existing-password-42"})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors.as_data()["__all__"][0].code, "too_many_attempts")

    def test_recovery_and_generation_have_independent_bounded_attempts(self):
        self.client.force_login(self.user)
        for endpoint, data in [("recovery_use", self.data),
                               ("recovery_generate", {"current_password": "wrong"})]:
            for _ in range(10):
                self.assertEqual(self.client.post(reverse(endpoint), data).status_code, 200)
            self.assertEqual(self.client.post(reverse(endpoint), data).status_code, 429)

    def test_peer_limit_prevents_username_rotation_and_ignores_forwarded_headers(self):
        request = RequestFactory().post("/", REMOTE_ADDR="192.0.2.1", HTTP_X_FORWARDED_FOR="fake")
        for index in range(60):
            self.assertTrue(allow_auth_attempt(request, "test", f"account-{index}"))
        request.META["HTTP_X_FORWARDED_FOR"] = "different"
        self.assertFalse(allow_auth_attempt(request, "test", "new-account"))
        self.assertEqual(AuthenticationAttempt.objects.count(), 61)
        AuthenticationAttempt.objects.update(window_started=timezone.now() - timedelta(days=2))
        self.assertTrue(allow_auth_attempt(request, "test", "fresh-account"))
        self.assertEqual(AuthenticationAttempt.objects.count(), 2)

    def test_post_endpoints_enforce_csrf_and_logout_rejects_get(self):
        client = Client(enforce_csrf_checks=True)
        for endpoint in ["login", "recovery_use", "recovery_request"]:
            self.assertEqual(client.post(reverse(endpoint), self.data).status_code, 403)
        client.force_login(self.user)
        for endpoint in ["password_change", "recovery_generate", "logout"]:
            self.assertEqual(client.post(reverse(endpoint), self.data).status_code, 403)
        self.assertEqual(client.get(reverse("logout")).status_code, 405)

    def test_recovery_invalidates_existing_sessions(self):
        self.client.force_login(self.user)
        code = issue_recovery_code(self.user.pk, "existing-password-42")
        self.assertTrue(redeem_recovery_code("owner", code, self.data)[0])
        self.assertRedirects(self.client.get(reverse("home")), reverse("login") + "?next=/",
                             fetch_redirect_response=False)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class RecoveryConcurrencyTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_only_one_concurrent_redemption_succeeds(self):
        user = User.objects.create_user(username="concurrent", password="Old-password-42")
        code = issue_recovery_code(user.pk, "Old-password-42")
        barrier = Barrier(2)

        def redeem():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return redeem_recovery_code("concurrent", code, {
                    "new_password1": "New-complex-password-42", "new_password2": "New-complex-password-42",
                })[0]
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(redeem) for _ in range(2)]
            self.assertEqual(sorted(f.result(timeout=20) for f in futures), [False, True])

    @skipUnlessDBFeature("has_select_for_update")
    def test_concurrent_attempts_cannot_overrun_account_limit(self):
        request = RequestFactory().post("/", REMOTE_ADDR="192.0.2.2")
        for _ in range(9):
            self.assertTrue(allow_auth_attempt(request, "parallel", "same"))
        barrier = Barrier(2)

        def attempt():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return allow_auth_attempt(request, "parallel", "same")
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(attempt) for _ in range(2)]
            self.assertEqual(sorted(f.result(timeout=20) for f in futures), [False, True])
