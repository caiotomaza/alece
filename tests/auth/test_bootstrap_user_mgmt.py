# SPDX-License-Identifier: GPL-3.0-only
"""Testes para configuração inicial (bootstrap) e gestão de usuários."""
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, Client
from django.urls import reverse
from django.utils import timezone

from apps.core.models import BootstrapToken, UserProfile
from apps.finance.models import FinancialProfile, ProfileGrant, Workspace, WorkspaceMembership


User = get_user_model()


class BootstrapSetupTests(TransactionTestCase):
    """Testes para configuração inicial (bootstrap)."""

    def setUp(self):
        self.client = Client()
        # Garantir que não há usuários - limpar em ordem correta para evitar foreign keys protegidas
        from django.core.management import call_command
        call_command('flush', verbosity=0, interactive=False)

    def test_setup_requires_no_existing_users(self):
        """Setup não deve funcionar se já existirem usuários."""
        User.objects.create_user(username="existing", password="pass123")
        response = self.client.get(reverse("setup"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/entrar/")

    def test_setup_get_shows_username_password_fields(self):
        """Página de setup deve mostrar campos de usuário e senha (sem token)."""
        response = self.client.get(reverse("setup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nome de usuário")
        self.assertContains(response, "Senha")
        self.assertContains(response, "Confirmação de senha")
        self.assertContains(response, "Criar Administrador")
        # Não deve conter campos removidos
        self.assertNotContains(response, "Token de Bootstrap")
        self.assertNotContains(response, "workspace_name")
        self.assertNotContains(response, "profile_name")
        self.assertNotContains(response, "monthly_income")

    def test_setup_post_creates_admin_and_default_workspace(self):
        """Setup cria admin, workspace 'Pessoal', perfil 'Principal' e grant total."""
        response = self.client.post(reverse("setup"), {
            "username": "admin",
            "password1": "adminpass123",
            "password2": "adminpass123",
        }, follow=True)

        # Deve redirecionar para /login/ após setup bem-sucedido
        self.assertRedirects(response, "/configuracoes/codigos/")
        self.assertTrue(User.objects.filter(username="admin").exists())
        admin_user = User.objects.get(username="admin")
        self.assertTrue(admin_user.check_password("adminpass123"))
        self.assertFalse(admin_user.is_staff)
        self.assertFalse(admin_user.is_superuser)

        # Verificar UserProfile
        self.assertTrue(UserProfile.objects.filter(user=admin_user).exists())

        # Verificar Workspace criado automaticamente como "Pessoal"
        self.assertTrue(Workspace.objects.filter(name="Pessoal").exists())
        workspace = Workspace.objects.get(name="Pessoal")
        self.assertEqual(workspace.created_by, admin_user)

        # Verificar Membership como ADMIN
        membership = WorkspaceMembership.objects.get(workspace=workspace, user=admin_user)
        self.assertEqual(membership.role, "admin")

        # Verificar Perfil Financeiro criado automaticamente como "Principal" (renda NULL)
        self.assertTrue(FinancialProfile.objects.filter(name="Principal").exists())
        profile = FinancialProfile.objects.get(name="Principal")
        self.assertEqual(profile.workspace, workspace)
        self.assertIsNone(profile.monthly_income)

        # Verificar Grant total
        grant = ProfileGrant.objects.get(membership=membership, profile=profile)
        self.assertTrue(grant.can_view)
        self.assertTrue(grant.can_edit)
        self.assertEqual(grant.overview_level, "edit")
        self.assertEqual(grant.accounts_level, "edit")
        self.assertEqual(grant.expenses_level, "edit")
        self.assertEqual(grant.investments_level, "edit")
        self.assertEqual(grant.movements_level, "edit")

        # Primeiro administrador entra diretamente na configuração obrigatória dos códigos.
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_setup_duplicate_username_fails(self):
        """Uma instalação já inicializada não reabre o formulário nem cria outro admin."""
        User.objects.create_user(username="admin", password="pass123")
        response = self.client.post(reverse("setup"), {
            "username": "admin",
            "password1": "adminpass123",
            "password2": "adminpass123",
        })
        self.assertRedirects(response, "/entrar/")
        self.assertEqual(User.objects.count(), 1)

    def test_setup_mismatched_passwords_fails(self):
        """Não deve permitir senhas diferentes."""
        response = self.client.post(reverse("setup"), {
            "username": "admin",
            "password1": "adminpass123",
            "password2": "differentpass",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "As senhas não coincidem.")

    def test_setup_weak_password_fails(self):
        """Não deve permitir senha fraca."""
        response = self.client.post(reverse("setup"), {
            "username": "admin",
            "password1": "123",
            "password2": "123",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mínimo 8 caracteres")


class UserManagementTests(TestCase):
    """Testes para gestão de usuários pelo Administrador."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username="admin", password="adminpass123")
        self.admin_userprofile = UserProfile.objects.create(user=self.admin)
        self.workspace = Workspace.objects.create(name="Núcleo Teste", created_by=self.admin)
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.admin, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.workspace, name="Perfil 1")
        ProfileGrant.objects.create(
            membership=WorkspaceMembership.objects.get(workspace=self.workspace, user=self.admin),
            profile=self.profile,
            can_view=True, can_edit=True,
            overview_level="edit", accounts_level="edit", expenses_level="edit",
            investments_level="edit", movements_level="edit",
        )
        self.client.force_login(self.admin)

    def test_user_management_list(self):
        """Listagem de usuários do workspace."""
        response = self.client.get(reverse("core:user-management", kwargs={"workspace_id": self.workspace.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "admin")

    def test_user_management_create_common(self):
        """Criar usuário Comum."""
        response = self.client.post(reverse("core:user-management", kwargs={"workspace_id": self.workspace.pk}), {
            "username": "comum",
            "password1": "comumpass123",
            "password2": "comumpass123",
            "role": "common",
            "is_active": True,
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username="comum").exists())
        comum = User.objects.get(username="comum")
        membership = WorkspaceMembership.objects.get(workspace=self.workspace, user=comum)
        self.assertEqual(membership.role, "common")
        self.assertTrue(UserProfile.objects.filter(user=comum).exists())

    def test_user_management_create_admin(self):
        """Criar usuário Administrador."""
        response = self.client.post(reverse("core:user-management", kwargs={"workspace_id": self.workspace.pk}), {
            "username": "admin2",
            "password1": "adminpass123",
            "password2": "adminpass123",
            "role": "admin",
            "is_active": True,
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        admin2 = User.objects.get(username="admin2")
        membership = WorkspaceMembership.objects.get(workspace=self.workspace, user=admin2)
        self.assertEqual(membership.role, "admin")

    def test_user_management_duplicate_username(self):
        """Não deve permitir username duplicado."""
        response = self.client.post(reverse("core:user-management", kwargs={"workspace_id": self.workspace.pk}), {
            "username": "admin",
            "password1": "adminpass123",
            "password2": "adminpass123",
            "role": "common",
            "is_active": True,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Este nome de usuário já está em uso.")

    def test_user_management_mismatched_passwords(self):
        """Não deve permitir senhas diferentes."""
        response = self.client.post(reverse("core:user-management", kwargs={"workspace_id": self.workspace.pk}), {
            "username": "novo",
            "password1": "pass1",
            "password2": "pass2",
            "role": "common",
            "is_active": True,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Os dois campos de senha não correspondem.")


class UserEditTests(TestCase):
    """Testes para edição de usuários."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username="admin", password="adminpass123")
        self.admin_userprofile = UserProfile.objects.create(user=self.admin)
        self.workspace = Workspace.objects.create(name="Núcleo Teste", created_by=self.admin)
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.admin, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.workspace, name="Perfil 1")
        ProfileGrant.objects.create(
            membership=WorkspaceMembership.objects.get(workspace=self.workspace, user=self.admin),
            profile=self.profile,
            can_view=True, can_edit=True,
            overview_level="edit", accounts_level="edit", expenses_level="edit",
            investments_level="edit", movements_level="edit",
        )
        # Criar segundo admin para testar proteção do último admin
        self.admin2 = User.objects.create_user(username="admin2", password="adminpass123")
        UserProfile.objects.create(user=self.admin2)
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.admin2, role="admin")
        ProfileGrant.objects.create(
            membership=WorkspaceMembership.objects.get(workspace=self.workspace, user=self.admin2),
            profile=self.profile,
            can_view=True, can_edit=True,
            overview_level="edit", accounts_level="edit", expenses_level="edit",
            investments_level="edit", movements_level="edit",
        )
        self.common = User.objects.create_user(username="comum", password="comumpass123")
        UserProfile.objects.create(user=self.common)
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.common, role="common")
        ProfileGrant.objects.create(
            membership=WorkspaceMembership.objects.get(workspace=self.workspace, user=self.common),
            profile=self.profile,
            can_view=True, can_edit=False,
            overview_level="view", accounts_level="none", expenses_level="view",
            investments_level="none", movements_level="none",
        )
        self.client.force_login(self.admin)

    def test_user_edit_change_role(self):
        """Alterar papel de Comum para Admin."""
        response = self.client.post(reverse("core:user-edit", kwargs={
            "workspace_id": self.workspace.pk, "user_id": self.common.pk
        }), {
            "username": "comum",
            "role": "admin",
            "is_active": True,
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        membership = WorkspaceMembership.objects.get(workspace=self.workspace, user=self.common)
        self.assertEqual(membership.role, "admin")

    def test_user_edit_cannot_remove_last_admin(self):
        """Não deve permitir remover o último admin ativo (auto-edição)."""
        # Tentar mudar admin de admin para common (seria o último admin ativo)
        response = self.client.post(reverse("core:user-edit", kwargs={
            "workspace_id": self.workspace.pk, "user_id": self.admin.pk
        }), {
            "username": "admin",
            "role": "common",
            "is_active": True,
        })
        self.assertEqual(response.status_code, 302)  # Auto-edição bloqueada
        self.assertRedirects(response, reverse("configuracoes-usuarios"))

    def test_user_edit_cannot_deactivate_last_admin(self):
        """Não deve permitir desativar o último admin ativo (auto-edição)."""
        # Tentar desativar admin (seria o último admin ativo)
        response = self.client.post(reverse("core:user-edit", kwargs={
            "workspace_id": self.workspace.pk, "user_id": self.admin.pk
        }), {
            "username": "admin",
            "role": "admin",
            "is_active": False,
        })
        self.assertEqual(response.status_code, 302)  # Auto-edição bloqueada
        self.assertRedirects(response, reverse("configuracoes-usuarios"))

    def test_user_edit_cannot_edit_self_role(self):
        """Admin não pode alterar seu próprio papel via edição."""
        response = self.client.get(reverse("core:user-edit", kwargs={
            "workspace_id": self.workspace.pk, "user_id": self.admin.pk
        }))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("configuracoes-usuarios"))


class UserPermissionTests(TestCase):
    """Testes para matriz de permissões."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username="admin", password="adminpass123")
        UserProfile.objects.create(user=self.admin)
        self.workspace = Workspace.objects.create(name="Núcleo Teste", created_by=self.admin)
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.admin, role="admin")
        self.profile1 = FinancialProfile.objects.create(workspace=self.workspace, name="Perfil 1")
        self.profile2 = FinancialProfile.objects.create(workspace=self.workspace, name="Perfil 2")
        self.profile3 = FinancialProfile.objects.create(workspace=self.workspace, name="Perfil 3")
        self.profile3.is_archived = True
        self.profile3.save()

        ProfileGrant.objects.create(
            membership=WorkspaceMembership.objects.get(workspace=self.workspace, user=self.admin),
            profile=self.profile1,
            can_view=True, can_edit=True,
            overview_level="edit", accounts_level="edit", expenses_level="edit",
            investments_level="edit", movements_level="edit",
        )
        self.client.force_login(self.admin)

    def test_grant_management_list(self):
        """Listar permissões existentes."""
        membership = WorkspaceMembership.objects.get(workspace=self.workspace, user=self.admin)
        response = self.client.get(reverse("core:grant-management", kwargs={
            "workspace_id": self.workspace.pk, "membership_id": membership.pk
        }))
        self.assertEqual(response.status_code, 200)

    def test_grant_management_update(self):
        """Atualizar permissões de um usuário."""
        membership = WorkspaceMembership.objects.get(workspace=self.workspace, user=self.admin)
        response = self.client.post(reverse("core:grant-management", kwargs={
            "workspace_id": self.workspace.pk, "membership_id": membership.pk
        }), {
            f"grant_{self.profile1.pk}_can_view": "on",
            f"grant_{self.profile1.pk}_can_edit": "on",
            f"grant_{self.profile1.pk}_overview_level": "edit",
            f"grant_{self.profile1.pk}_accounts_level": "view",
            f"grant_{self.profile1.pk}_expenses_level": "edit",
            f"grant_{self.profile1.pk}_investments_level": "none",
            f"grant_{self.profile1.pk}_movements_level": "view",

            f"grant_{self.profile2.pk}_can_view": "on",
            f"grant_{self.profile2.pk}_can_edit": "",
            f"grant_{self.profile2.pk}_overview_level": "view",
            f"grant_{self.profile2.pk}_accounts_level": "none",
            f"grant_{self.profile2.pk}_expenses_level": "none",
            f"grant_{self.profile2.pk}_investments_level": "none",
            f"grant_{self.profile2.pk}_movements_level": "none",

            f"grant_{self.profile3.pk}_can_view": "",
            f"grant_{self.profile3.pk}_can_edit": "",
        }, follow=True)

        self.assertEqual(response.status_code, 200)

        # Verificar grants salvos
        grant1 = ProfileGrant.objects.get(membership__workspace=self.workspace, profile=self.profile1)
        self.assertTrue(grant1.can_view)
        self.assertTrue(grant1.can_edit)
        self.assertEqual(grant1.overview_level, "edit")
        self.assertEqual(grant1.accounts_level, "view")
        self.assertEqual(grant1.expenses_level, "edit")
        self.assertEqual(grant1.investments_level, "none")
        self.assertEqual(grant1.movements_level, "view")

        grant2 = ProfileGrant.objects.get(membership__workspace=self.workspace, profile=self.profile2)
        self.assertTrue(grant2.can_view)
        self.assertFalse(grant2.can_edit)
        self.assertEqual(grant2.overview_level, "view")

    def test_grant_archived_profile_disabled(self):
        """Perfis arquivados não devem permitir alteração de permissões."""
        membership = WorkspaceMembership.objects.get(workspace=self.workspace, user=self.admin)
        response = self.client.get(reverse("core:grant-management", kwargs={
            "workspace_id": self.workspace.pk, "membership_id": membership.pk
        }))
        self.assertEqual(response.status_code, 200)
        # Perfil 3 está arquivado, campos devem estar disabled no template
        self.assertContains(response, "disabled")


class SecurityTests(TestCase):
    """Testes de segurança e isolamento."""

    def setUp(self):
        self.client = Client()
        self.admin1 = User.objects.create_user(username="admin1", password="pass123")
        UserProfile.objects.create(user=self.admin1)
        self.ws1 = Workspace.objects.create(name="WS1", created_by=self.admin1)
        WorkspaceMembership.objects.create(workspace=self.ws1, user=self.admin1, role="admin")
        self.profile1 = FinancialProfile.objects.create(workspace=self.ws1, name="Perfil WS1")

        self.admin2 = User.objects.create_user(username="admin2", password="pass123")
        UserProfile.objects.create(user=self.admin2)
        self.ws2 = Workspace.objects.create(name="WS2", created_by=self.admin2)
        WorkspaceMembership.objects.create(workspace=self.ws2, user=self.admin2, role="admin")
        self.profile2 = FinancialProfile.objects.create(workspace=self.ws2, name="Perfil WS2")

    def test_admin_cannot_access_other_workspace_users(self):
        """Admin do WS1 não deve acessar usuários do WS2."""
        self.client.force_login(self.admin1)
        response = self.client.get(reverse("core:user-management", kwargs={"workspace_id": self.ws2.pk}))
        # Deve negar acesso (403 ou redirect)
        self.assertNotEqual(response.status_code, 200)

    def test_admin_cannot_edit_other_workspace_user(self):
        """Admin do WS1 não deve editar usuários do WS2."""
        self.client.force_login(self.admin1)
        response = self.client.get(reverse("core:user-edit", kwargs={
            "workspace_id": self.ws2.pk, "user_id": self.admin2.pk
        }))
        self.assertNotEqual(response.status_code, 200)


class BootstrapTokenTests(TestCase):
    """Testes para o modelo BootstrapToken."""

    def test_validate_token_valid(self):
        import hashlib
        import secrets

        raw = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        token = BootstrapToken.objects.create(
            token_hash=token_hash,
            expires_at=timezone.now() + timezone.timedelta(hours=24),
        )
        validated = BootstrapToken.validate_token(raw)
        self.assertEqual(validated, token)

    def test_validate_token_expired(self):
        import hashlib
        import secrets

        raw = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        BootstrapToken.objects.create(
            token_hash=token_hash,
            expires_at=timezone.now() - timezone.timedelta(hours=1),
        )
        validated = BootstrapToken.validate_token(raw)
        self.assertIsNone(validated)

    def test_validate_token_used(self):
        import hashlib
        import secrets
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(username="test", password="pass")

        raw = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        token = BootstrapToken.objects.create(
            token_hash=token_hash,
            expires_at=timezone.now() + timezone.timedelta(hours=24),
        )
        token.mark_used(user)

        validated = BootstrapToken.validate_token(raw)
        self.assertIsNone(validated)


class InitializationRedirectTests(TransactionTestCase):
    """Testes de redirecionamento para setup quando não inicializado."""

    def setUp(self):
        self.client = Client()
        from django.core.management import call_command
        call_command('flush', verbosity=0, interactive=False)

    def test_home_redirects_to_setup_when_not_initialized(self):
        """Home deve redirecionar para setup se nenhum usuário existe."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/configuracao-inicial/", response.url)

    def test_login_redirects_to_setup_when_not_initialized(self):
        """Login deve redirecionar para setup se sistema não inicializado."""
        response = self.client.get("/entrar/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/configuracao-inicial/", response.url)

    def test_setup_accessible_when_not_initialized(self):
        """Setup deve ser acessível sem inicialização."""
        response = self.client.get("/configuracao-inicial/")
        self.assertEqual(response.status_code, 200)

    def test_home_redirects_to_login_when_initialized(self):
        """Home deve redirecionar para login se inicializado mas não autenticado."""
        User.objects.create_user(username="test", password="pass")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/entrar/", response.url)


class UserDeactivationTests(TestCase):
    """Testes de desativação e bloqueio de usuários."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username="admin", password="adminpass123")
        UserProfile.objects.create(user=self.admin)
        self.workspace = Workspace.objects.create(name="WS", created_by=self.admin)
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.admin, role="admin")
        self.profile = FinancialProfile.objects.create(workspace=self.workspace, name="Perfil")
        ProfileGrant.objects.create(
            membership=WorkspaceMembership.objects.get(workspace=self.workspace, user=self.admin),
            profile=self.profile,
            can_view=True, can_edit=True,
            overview_level="edit", accounts_level="edit", expenses_level="edit",
            investments_level="edit", movements_level="edit",
        )
        self.common = User.objects.create_user(username="comum", password="comumpass123")
        UserProfile.objects.create(user=self.common)
        WorkspaceMembership.objects.create(workspace=self.workspace, user=self.common, role="common")
        self.client.force_login(self.admin)

    def test_revoke_sessions(self):
        """Revogar sessões de outro usuário."""
        # Criar sessão simulada
        from django.contrib.sessions.models import Session
        from django.utils import timezone

        from django.contrib.sessions.backends.db import SessionStore
        signed = SessionStore()
        signed["_auth_user_id"] = str(self.common.pk)
        signed.save()
        session_key = signed.session_key

        response = self.client.post(reverse("core:user-revoke-sessions", kwargs={
            "workspace_id": self.workspace.pk, "user_id": self.common.pk
        }), follow=True)

        self.assertEqual(response.status_code, 200)
        # Sessão deve ter sido removida
        self.assertFalse(Session.objects.filter(session_key=session_key).exists())

    def test_cannot_revoke_own_sessions(self):
        """Não pode revogar próprias sessões."""
        response = self.client.post(reverse("core:user-revoke-sessions", kwargs={
            "workspace_id": self.workspace.pk, "user_id": self.admin.pk
        }), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "não pode revogar suas próprias sessões")

    def test_password_reset_by_admin(self):
        """Admin pode redefinir senha de outro usuário."""
        response = self.client.post(reverse("core:user-password-reset", kwargs={
            "workspace_id": self.workspace.pk, "user_id": self.common.pk
        }), {
            "new_password1": "novasenha123",
            "new_password2": "novasenha123",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.common.refresh_from_db()
        self.assertTrue(self.common.check_password("novasenha123"))

    def test_cannot_reset_own_password_via_admin(self):
        """Admin não pode redefinir própria senha via gestão de usuários."""
        response = self.client.post(reverse("core:user-password-reset", kwargs={
            "workspace_id": self.workspace.pk, "user_id": self.admin.pk
        }), {
            "new_password1": "novasenha123",
            "new_password2": "novasenha123",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alterar senha")
