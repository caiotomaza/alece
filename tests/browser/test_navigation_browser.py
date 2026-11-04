# SPDX-License-Identifier: GPL-3.0-only
"""Real Chromium journeys with synthetic data and isolated live PostgreSQL."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.finance.models import FinancialProfile, Workspace, WorkspaceMembership
from apps.finance.profile_selection import SESSION_KEY
from django.contrib.sessions.backends.db import SessionStore

pytestmark = pytest.mark.browser


@pytest.fixture
def browser_identity(transactional_db, client, live_server, alece_page):
    owner = get_user_model().objects.create_user(username="alece-browser-owner", password="Sample12345!@")
    workspace = Workspace.objects.create(name="Ambiente sintetico", created_by=owner)
    WorkspaceMembership.objects.create(workspace=workspace, user=owner, role="admin")
    profile = FinancialProfile.objects.create(workspace=workspace, name="Principal")
    FinancialProfile.objects.create(workspace=workspace, name="Outro")
    client.force_login(owner)
    alece_page.context.add_cookies([{"name": "sessionid", "value":client.cookies["sessionid"].value, "url":live_server.url}])
    return alece_page, live_server, profile


def test_five_sections_are_real_pages_without_ids(browser_identity):
    page, server, profile = browser_identity
    for route in ("visao-geral", "despesas", "investimentos", "movimentacoes", "configuracoes"):
        resp = page.goto(server.url + reverse(route), wait_until="domcontentloaded")
        assert resp is not None and resp.status == 200, route
        assert page.locator("main").count() > 0, route
        assert str(profile.pk) not in page.url.split("/")[-2:], route


def test_profile_choice_survives_financial_navigation(browser_identity):
    page, server, profile = browser_identity
    resp = page.goto(server.url + reverse("visao-geral") + f"?profiles={profile.pk}")
    assert resp is not None and resp.status == 200
    for route in ("despesas", "investimentos", "movimentacoes", "visao-geral"):
        resp = page.goto(server.url + reverse(route))
        assert resp is not None and resp.status == 200
        # The selection belongs to the authenticated session, not an untrusted URL.
        cookie = page.context.cookies(server.url)
        session_key = next(c["value"] for c in cookie if c["name"] == "sessionid")
        state = SessionStore(session_key=session_key).load()
        assert state[SESSION_KEY]["profile_id"] == profile.pk, route



def test_common_account_cannot_open_admin_pages(transactional_db, live_server, alece_page, client):
    user = get_user_model().objects.create_user(username="alece-browser-common",password="Sample12345!@")
    ws = Workspace.objects.create(name="Acesso comum sintetico", created_by=user)
    WorkspaceMembership.objects.create(workspace=ws, user=user, role="common")
    FinancialProfile.objects.create(workspace=ws, name="Principal")
    client.force_login(user)
    alece_page.context.add_cookies([{"name":"sessionid", "value":client.cookies["sessionid"].value,"url":live_server.url}])
    for route in ("configuracoes-usuarios", "configuracoes-perfis", "configuracoes-apis", "logs", "relatorios"):
        res = alece_page.goto(live_server.url + reverse(route),wait_until="domcontentloaded")
        assert res is not None and res.status == 403, route


def test_admin_management_uses_full_pages_in_mobile_view(browser_identity):
    page, server, _profile = browser_identity
    page.set_viewport_size({"width":390,"height":844})
    for route in ("configuracoes-usuarios", "configuracoes-perfis", "configuracoes-apis"):
        response=page.goto(server.url + reverse(route), wait_until="domcontentloaded")
        assert response is not None and response.status == 200, route
        assert page.locator("main").count() == 1
        # Avoid a full-screen dialog substituted for a management page.
        assert not page.locator('dialog[open]').count(), route
