# SPDX-License-Identifier: GPL-3.0-only
"""Regressão da preferência de perfil entre as abas e isolamento de permissões."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.finance.models import FinancialProfile, ProfileGrant, Workspace, WorkspaceMembership
from apps.finance.profile_selection import SESSION_KEY


class ProfileNavigationStateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = get_user_model().objects.create_user(username="nav-admin", password="TestPass123!")
        cls.member = get_user_model().objects.create_user(username="nav-member", password="TestPass123!")
        cls.workspace = Workspace.objects.create(name="Casa", created_by=cls.admin)
        WorkspaceMembership.objects.create(
            workspace=cls.workspace, user=cls.admin, role=WorkspaceMembership.Role.ADMIN,
        )
        cls.member_link = WorkspaceMembership.objects.create(
            workspace=cls.workspace, user=cls.member, role=WorkspaceMembership.Role.COMMON,
        )
        cls.principal = FinancialProfile.objects.create(workspace=cls.workspace, name="Principal")
        cls.outro = FinancialProfile.objects.create(workspace=cls.workspace, name="Outro")
        ProfileGrant.objects.create(
            profile=cls.principal, membership=cls.member_link,
            can_view=True, can_edit=False,
            expenses_level=ProfileGrant.Level.VIEW,
            investments_level=ProfileGrant.Level.NONE,
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_keeps_principal_when_switching_pages_and_settings(self):
        url = reverse("despesas") + f"?profiles={self.principal.pk}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([s["profile"].pk for s in response.context["sections"]], [self.principal.pk])
        for name in ("investimentos", "visao-geral", "movimentacoes"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)
            self.assertEqual([s["profile"].pk for s in response.context["sections"]], [self.principal.pk])
            self.assertContains(response, "Principal")
        settings = self.client.get(reverse("configuracoes"))
        self.assertEqual(settings.status_code, 200)
        self.assertContains(settings, 'href="/investimentos/"')
        self.assertEqual(self.client.session[SESSION_KEY]["profile_id"], self.principal.pk)

    def test_clear_all_profiles_is_explicit_and_persistent(self):
        self.client.get(reverse("despesas") + f"?profiles={self.principal.pk}")
        response = self.client.get(reverse("investimentos") + "?profiles=all")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["sections"]), 2)
        self.assertNotIn(SESSION_KEY, self.client.session)
        response = self.client.get(reverse("despesas"))
        self.assertEqual(len(response.context["sections"]), 2)

    def test_invalid_or_unavailable_profile_cannot_be_selected(self):
        self.assertEqual(self.client.get(reverse("despesas") + "?profiles=999999").status_code, 400)
        self.assertEqual(self.client.get(reverse("despesas") + "?profiles=abc").status_code, 400)

    def test_member_without_investments_access_does_not_fall_back_to_other_profiles(self):
        self.client.force_login(self.member)
        response = self.client.get(reverse("despesas") + f"?profiles={self.principal.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([s["profile"].pk for s in response.context["sections"]], [self.principal.pk])
        response = self.client.get(reverse("investimentos"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["sections"], [])
        self.assertEqual(self.client.session[SESSION_KEY]["profile_id"], self.principal.pk)
        self.assertContains(response, "Principal")
        self.assertEqual(self.client.get(reverse("despesas") + f"?profiles={self.outro.pk}").status_code, 400)

    def test_archived_selection_is_discarded(self):
        self.client.get(reverse("despesas") + f"?profiles={self.principal.pk}")
        self.principal.is_archived = True
        self.principal.save(update_fields=["is_archived"])
        response = self.client.get(reverse("investimentos"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertEqual([s["profile"].pk for s in response.context["sections"]], [self.outro.pk])

    def test_settings_selector_updates_preference(self):
        url = reverse("configuracoes") + f"?profiles={self.principal.pk}"
        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.get(reverse("despesas"))
        self.assertEqual([s["profile"].pk for s in response.context["sections"]], [self.principal.pk])
        self.assertEqual(self.client.get(reverse("configuracoes") + "?profiles=all").status_code, 200)
        self.assertNotIn(SESSION_KEY, self.client.session)
