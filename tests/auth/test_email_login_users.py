# SPDX-License-Identifier: GPL-3.0-only
"""Safety regression: optional email login with unambiguous identity."""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from apps.core.login_forms import EmailOrUsernameAuthenticationForm
from apps.core.forms import UserManagementForm, UserEditForm


class EmailLoginTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="contateste", email="Contato@Exemplo.org", password="StrongPass456!example")
        self.request = RequestFactory().post("/entrar/")

    def login_form(self, username, password="StrongPass456!example"):
        return EmailOrUsernameAuthenticationForm(self.request, data={"username": username, "password": password})

    def test_username_and_optional_email_login(self):
        for value in ("contateste", "CONTATO@exemplo.org", "Contato@Exemplo.org"):
            with self.subTest(value=value):
                form = self.login_form(value)
                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(form.get_user(), self.user)

    def test_incorrect_password_or_inactive(self):
        self.assertFalse(self.login_form("Contato@Exemplo.org", "badpassword").is_valid())
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.assertFalse(self.login_form("Contato@Exemplo.org").is_valid())

    def test_legacy_ambiguous_email_fails_closed(self):
        get_user_model().objects.create_user(username="outra", email="contato@exemplo.org", password="StrongPass456!example")
        self.assertFalse(self.login_form("contato@exemplo.org").is_valid())
        self.assertTrue(self.login_form("contateste").is_valid())

    def test_edit_email_optional_and_unique(self):
        form = UserEditForm(data={"username": "contateste", "email": "", "role": "common", "is_active": "on"}, instance=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().email, "")
        get_user_model().objects.create_user(username="second", email="other@example.org")
        form = UserEditForm(data={"username": "contateste", "email": "OTHER@example.org", "role": "common", "is_active": "on"}, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
