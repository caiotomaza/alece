# SPDX-License-Identifier: GPL-3.0-only
"""Testes para autenticação, recuperação offline e permissões."""
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from apps.core.models import UserProfile
from apps.core.permissions import (
    get_user_workspaces,
    user_has_workspace_access,
    user_is_workspace_admin,
    user_can_view_profile,
    user_can_edit_profile,
    get_accessible_profiles,
    get_editable_profiles,
    require_profile_view,
    require_profile_edit,
    PermissionError,
)
from apps.finance.models import FinancialProfile, ProfileGrant, Workspace, WorkspaceMembership


User = get_user_model()


class AuthenticationViewsTests(TestCase):
    """Testes para views de autenticação."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.user2 = User.objects.create_user(username="testuser2", password="testpass123")

    def test_login_get(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Entrar no ALECE")

    def test_login_post_valid(self):
        response = self.client.post(reverse("login"), {"username": "testuser", "password": "testpass123"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_post_invalid(self):
        response = self.client.post(reverse("login"), {"username": "testuser", "password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Usuário ou senha inválidos")
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_password_change(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("password_change"), {
            "old_password": "testpass123",
            "new_password1": "newpass456",
            "new_password2": "newpass456",
        })
        self.assertEqual(response.status_code, 302)
        # Verificar que a senha foi alterada
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpass456"))


class RecoveryCodeTests(TestCase):
    """Testes para código de recuperação offline."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="recoveryuser", password="oldpass123")

    def test_recovery_request_get(self):
        response = self.client.get(reverse("recovery_request"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Recuperação offline")

    def test_recovery_request_post_generates_code(self):
        response = self.client.post(reverse("recovery_request"), {"username": "recoveryuser"})
        self.assertEqual(response.status_code, 200)
        # Deve exibir o código
        self.assertContains(response, "Código de recuperação gerado")
        # Verificar que o hash foi salvo
        self.user.refresh_from_db()
        profile = self.user.profile
        self.assertIsNotNone(profile.recovery_code_hash)
        self.assertIsNotNone(profile.recovery_code_created)

    def test_recovery_request_nonexistent_user(self):
        # Não deve revelar se o usuário existe
        response = self.client.post(reverse("recovery_request"), {"username": "nonexistent"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Se o usuário existir")

    def test_recovery_use_valid_code(self):
        # Gerar código conhecido diretamente no perfil
        import hashlib
        from django.utils import timezone
        from apps.core.models import UserProfile
        code = "test-recovery-code-123"
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.recovery_code_hash = hashlib.sha256(code.encode()).hexdigest()
        profile.recovery_code_created = timezone.now()
        profile.save(update_fields=["recovery_code_hash", "recovery_code_created", "updated_at"])

        # Usar o código
        response = self.client.post(reverse("recovery_use"), {
            "username": "recoveryuser",
            "code": code,
            "new_password1": "newpass789",
            "new_password2": "newpass789",
        })
        # Verificar que a senha foi alterada
        self.user.refresh_from_db()
        # Verificar que o código foi invalidado
        profile.refresh_from_db()
        self.assertEqual(response.status_code, 302, f"Expected 302, got {response.status_code}. Content: {response.content[:500]}")
        self.assertTrue(self.user.check_password("newpass789"), f"Password not changed. Hash: {self.user.password}")
        self.assertIsNone(profile.recovery_code_hash, f"Code not invalidated: {profile.recovery_code_hash}")

    def test_recovery_use_invalid_code(self):
        response = self.client.post(reverse("recovery_use"), {
            "username": "recoveryuser",
            "code": "wrong-code",
            "new_password1": "newpass789",
            "new_password2": "newpass789",
        })
        self.assertEqual(response.status_code, 200)
        # Mensagem pode variar: "Nenhum código..." ou "Código inválido"
        content = response.content.decode()
        self.assertTrue(
            "inválido" in content or "ativo" in content,
            f"Mensagem de erro esperada não encontrada: {content[:200]}"
        )

    def test_recovery_use_mismatched_passwords(self):
        response = self.client.post(reverse("recovery_use"), {
            "username": "recoveryuser",
            "code": "some-code",
            "new_password1": "pass1",
            "new_password2": "pass2",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "As senhas não coincidem")

    def test_recovery_generate_logged_in(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("recovery_generate"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Novo código de recuperação gerado")
        self.user.refresh_from_db()
        profile = self.user.profile
        self.assertIsNotNone(profile.recovery_code_hash)


class PermissionTests(TestCase):
    """Testes para sistema de permissões e isolamento."""

    def setUp(self):
        self.user1 = User.objects.create_user(username="user1", password="pass123")
        self.user2 = User.objects.create_user(username="user2", password="pass123")
        self.user3 = User.objects.create_user(username="user3", password="pass123")

        # Workspace 1: user1 é admin, user2 é common
        self.ws1 = Workspace.objects.create(name="Núcleo 1", created_by=self.user1)
        WorkspaceMembership.objects.create(workspace=self.ws1, user=self.user1, role=WorkspaceMembership.Role.ADMIN)
        WorkspaceMembership.objects.create(workspace=self.ws1, user=self.user2, role=WorkspaceMembership.Role.COMMON)

        # Workspace 2: user3 é admin
        self.ws2 = Workspace.objects.create(name="Núcleo 2", created_by=self.user3)
        WorkspaceMembership.objects.create(workspace=self.ws2, user=self.user3, role=WorkspaceMembership.Role.ADMIN)

        # Perfis no workspace 1
        self.profile1 = FinancialProfile.objects.create(workspace=self.ws1, name="Perfil 1")
        self.profile2 = FinancialProfile.objects.create(workspace=self.ws1, name="Perfil 2")
        # Perfil no workspace 2
        self.profile3 = FinancialProfile.objects.create(workspace=self.ws2, name="Perfil 3")

        # Grants: user1 (admin) tem acesso a tudo no ws1
        ProfileGrant.objects.create(membership=self.ws1.memberships.get(user=self.user1), profile=self.profile1, can_view=True, can_edit=True)
        ProfileGrant.objects.create(membership=self.ws1.memberships.get(user=self.user1), profile=self.profile2, can_view=True, can_edit=True)
        # user2 (common) só vê perfil1, não edita
        ProfileGrant.objects.create(membership=self.ws1.memberships.get(user=self.user2), profile=self.profile1, can_view=True, can_edit=False)
        # user3 tem acesso ao perfil3
        ProfileGrant.objects.create(membership=self.ws2.memberships.get(user=self.user3), profile=self.profile3, can_view=True, can_edit=True)

    def test_user1_has_ws1_access(self):
        self.assertTrue(user_has_workspace_access(self.user1, self.ws1.pk))
        self.assertTrue(user_is_workspace_admin(self.user1, self.ws1.pk))

    def test_user2_has_ws1_access_not_admin(self):
        self.assertTrue(user_has_workspace_access(self.user2, self.ws1.pk))
        self.assertFalse(user_is_workspace_admin(self.user2, self.ws1.pk))

    def test_user3_no_ws1_access(self):
        self.assertFalse(user_has_workspace_access(self.user3, self.ws1.pk))
        self.assertFalse(user_is_workspace_admin(self.user3, self.ws1.pk))

    def test_user1_can_view_both_profiles_ws1(self):
        self.assertTrue(user_can_view_profile(self.user1, self.profile1.pk))
        self.assertTrue(user_can_view_profile(self.user1, self.profile2.pk))
        self.assertTrue(user_can_edit_profile(self.user1, self.profile1.pk))
        self.assertTrue(user_can_edit_profile(self.user1, self.profile2.pk))

    def test_user2_can_only_view_profile1(self):
        self.assertTrue(user_can_view_profile(self.user2, self.profile1.pk))
        self.assertFalse(user_can_edit_profile(self.user2, self.profile1.pk))
        self.assertFalse(user_can_view_profile(self.user2, self.profile2.pk))
        self.assertFalse(user_can_view_profile(self.user2, self.profile3.pk))

    def test_user3_can_access_own_ws_only(self):
        self.assertTrue(user_can_view_profile(self.user3, self.profile3.pk))
        self.assertTrue(user_can_edit_profile(self.user3, self.profile3.pk))
        self.assertFalse(user_can_view_profile(self.user3, self.profile1.pk))
        self.assertFalse(user_can_view_profile(self.user3, self.profile2.pk))

    def test_get_accessible_profiles(self):
        profiles1 = get_accessible_profiles(self.user1)
        self.assertEqual(profiles1.count(), 2)
        self.assertIn(self.profile1, profiles1)
        self.assertIn(self.profile2, profiles1)

        profiles2 = get_accessible_profiles(self.user2)
        self.assertEqual(profiles2.count(), 1)
        self.assertIn(self.profile1, profiles2)

        profiles3 = get_accessible_profiles(self.user3)
        self.assertEqual(profiles3.count(), 1)
        self.assertIn(self.profile3, profiles3)

    def test_get_editable_profiles(self):
        editable1 = get_editable_profiles(self.user1)
        self.assertEqual(editable1.count(), 2)

        editable2 = get_editable_profiles(self.user2)
        self.assertEqual(editable2.count(), 0)

        editable3 = get_editable_profiles(self.user3)
        self.assertEqual(editable3.count(), 1)
        self.assertIn(self.profile3, editable3)

    def test_require_profile_view_raises_on_no_access(self):
        with self.assertRaises(PermissionError):
            require_profile_view(self.user2, self.profile2.pk)
        with self.assertRaises(PermissionError):
            require_profile_view(self.user3, self.profile1.pk)

    def test_require_profile_edit_raises_on_no_edit(self):
        with self.assertRaises(PermissionError):
            require_profile_edit(self.user2, self.profile1.pk)
        with self.assertRaises(PermissionError):
            require_profile_edit(self.user3, self.profile1.pk)

    def test_require_profile_ownership(self):
        # user1 pode acessar perfil1
        profile = require_profile_view(self.user1, self.profile1.pk)
        self.assertEqual(profile.pk, self.profile1.pk)
        # user3 não pode acessar perfil1
        with self.assertRaises(PermissionError):
            require_profile_view(self.user3, self.profile1.pk)


class AuthorizationIntegrationTests(TestCase):
    """Testes de integração: views protegidas por permissões."""

    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username="user1", password="pass123")
        self.user2 = User.objects.create_user(username="user2", password="pass123")
        self.ws1 = Workspace.objects.create(name="Núcleo 1", created_by=self.user1)
        WorkspaceMembership.objects.create(workspace=self.ws1, user=self.user1, role=WorkspaceMembership.Role.ADMIN)
        WorkspaceMembership.objects.create(workspace=self.ws1, user=self.user2, role=WorkspaceMembership.Role.COMMON)
        self.profile1 = FinancialProfile.objects.create(workspace=self.ws1, name="Perfil 1")
        ProfileGrant.objects.create(membership=self.ws1.memberships.get(user=self.user1), profile=self.profile1, can_view=True, can_edit=True)
        ProfileGrant.objects.create(membership=self.ws1.memberships.get(user=self.user2), profile=self.profile1, can_view=True, can_edit=False)

    def test_unauthenticated_redirects_to_login(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_authenticated_user_sees_home(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_user_without_profile_access_cannot_see_profile_data(self):
        """Usuário sem grant não deve acessar dados do perfil."""
        # Esta parte será testada quando houver views de perfil
        pass