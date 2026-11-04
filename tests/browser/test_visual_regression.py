# SPDX-License-Identifier: GPL-3.0-only
"""Snapshots da aplicação Django REAL, com PostgreSQL exclusivo de CI e dados sintéticos.

MODO compare (padrão): baseline inexistente/diferente REPROVA e anexa evidências.
MODO capture: produz somente CANDIDATOS para revisão; nunca escreve na baseline.
"""
import json
import os
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from apps.core.models import AIProviderConfig, UserProfile
from apps.finance.models import (
    BankAccount, FinancialProfile, InvestmentPosition, RecurringExpense,
    TransactionBatch, UnexpectedExpense, Workspace, WorkspaceMembership,
)
from scripts.visual_regression.comparator import compare_png

pytestmark = [pytest.mark.browser, pytest.mark.visual]
ROOT = Path(__file__).resolve().parents[2]
BASELINES = ROOT / "tests/browser/visual_baselines"
EVIDENCE = Path(os.environ.get("ALECE_TEST_RESULTS", "test-results")) / "visual"
VIEWPORTS = {"320": (320, 720), "390": (390, 844), "768": (768, 1024),
             "1280": (1280, 800), "1920": (1920, 1080)}
SCENARIOS = (
    "overview_empty", "overview_filled", "expenses_empty", "expenses_filled",
    "investments_empty", "investments_filled", "movements_filled", "import_upload",
    "settings_common", "admin_users", "admin_profiles", "admin_ai",
    "profile_edit", "expense_edit", "logs", "reports", "dropdown_open", "modal_invalid",
    "message_success", "message_error", "forbidden", "reports_financial",
    "filter_focus", "button_hover",
)
FILL = {"overview_filled", "expenses_filled", "investments_filled", "movements_filled",
        "expense_edit", "import_upload", "reports", "reports_financial",
        "dropdown_open", "modal_invalid", "filter_focus", "button_hover"}
COMMON = {"settings_common", "forbidden"}


def _require_isolation():
    """Falhar antes de criar usuários se o alvo puder ser uma instalação existente."""
    db = settings.DATABASES["default"]
    assert os.environ.get("ALECE_TEST_ISOLATED") == "1", "Suite visual exige isolamento explícito"
    assert os.environ.get("DJANGO_SETTINGS_MODULE") == "config.test_settings"
    # pytest-django can rename alece_test to test_alece_test after creating its throwaway DB.
    assert db["NAME"] in ("alece_test", "test_alece_test"), (
        "Proibido apontar snapshots para banco não efêmero"
    )
    assert db["HOST"] in ("postgres", "127.0.0.1", "localhost"), "Host PostgreSQL não autorizado"
    assert settings.DEBUG is False, "Requer configuração de teste previsível"
    assert os.environ.get("ALECE_VISUAL_MODE", "compare") in ("compare", "capture")


@pytest.fixture
def visual_identity(transactional_db, client, live_server, page, request):
    _require_isolation()
    scenario = request.param
    common = scenario in COMMON
    user = get_user_model().objects.create_user(
        username="visual-common" if common else "visual-admin",
        password="VisualOnly!000123")
    UserProfile.objects.update_or_create(user=user, defaults={"theme": "light"})
    workspace = Workspace.objects.create(name="Espaço Visual Fictício", created_by=user)
    WorkspaceMembership.objects.create(workspace=workspace, user=user,
                                       role="common" if common else "admin")
    profile = FinancialProfile.objects.create(
        workspace=workspace, name="Perfil sintético", monthly_income=Decimal("3200.00")
        if scenario in FILL else None)
    second = FinancialProfile.objects.create(workspace=workspace, name="Perfil adicional")
    FinancialProfile.objects.filter(pk__in=(profile.pk, second.pk)).update(
        created_at=datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc))
    expense = None
    if scenario in FILL:
        BankAccount.objects.create(profile=profile, name="Conta de demonstração", kind="bank",
                                   balance=Decimal("1800.50"))
        expense = RecurringExpense.objects.create(
            profile=profile, name="Moradia de teste", category="essential",
            amount=Decimal("850.00"), due_day=5)
        InvestmentPosition.objects.create(profile=profile, name="Reserva fictícia",
                                          category="reserve", applied_amount=Decimal("400.00"),
                                          current_value=Decimal("420.00"), recorded_on=date(2026, 10, 18))
        event = UnexpectedExpense.objects.create(
            profile=profile, name="Compra simulada", amount=Decimal("39.90"),
            recorded_on=date(2026, 10, 18))
        TransactionBatch.objects.create(profile=profile, kind="unexpected", unexpected_expense=event,
                                        amount=Decimal("39.90"), occurred_on=date(2026, 10, 18),
                                        created_by=user)
        # A movimentação deve obedecer ao mesmo contrato de partidas do domínio.
        from apps.finance.models import JournalEntry
        batch = TransactionBatch.objects.get(unexpected_expense=event)
        JournalEntry.objects.create(batch=batch, account_code="visual:debit", debit=Decimal("39.90"))
        JournalEntry.objects.create(batch=batch, account_code="visual:credit", credit=Decimal("39.90"))
    if scenario == "admin_ai":
        AIProviderConfig.objects.create(
            workspace=workspace, name="Provedor fictício", model_name="modelo-local",
            endpoint="https://example.invalid/v1/chat/completions", sections=["expenses"],
            enabled=False)
    client.force_login(user)
    if scenario in ("message_success", "message_error"):
        from django.contrib.messages.storage.session import SessionStorage
        from django.test import RequestFactory
        from django.http import HttpResponse
        msg_request = RequestFactory().get("/")
        msg_request.session = client.session
        storage = SessionStorage(msg_request)
        storage.add(25 if scenario == "message_success" else 40,
                    "Operação simulada concluída." if scenario == "message_success"
                    else "Falha simulada: reveja o formulário.")
        storage.update(HttpResponse())
        msg_request.session.save()
    page.context.add_cookies([{"name": settings.SESSION_COOKIE_NAME,
                               "value": client.cookies[settings.SESSION_COOKIE_NAME].value,
                               "url": live_server.url}])
    return scenario, page, live_server, workspace, profile, second, expense


def _route(scenario, workspace, profile, expense):
    if scenario.startswith("overview") or scenario in ("dropdown_open", "message_success", "message_error", "button_hover"):
        return reverse("visao-geral") + "?month=2026-10"
    if scenario.startswith("expenses"):
        return reverse("despesas") + "?month=2026-10"
    if scenario.startswith("investments"):
        return reverse("investimentos") + "?month=2026-10"
    if scenario == "movements_filled":
        return reverse("movimentacoes") + "?month=2026-10"
    if scenario == "import_upload":
        return reverse("finance:import-upload", args=[profile.pk])
    if scenario == "forbidden":
        return reverse("configuracoes-usuarios")
    if scenario == "settings_common" or scenario == "modal_invalid":
        return reverse("configuracoes")
    if scenario.startswith("admin_"):
        panel = {"admin_users": "configuracoes-usuarios", "admin_profiles": "configuracoes-perfis",
                 "admin_ai": "configuracoes-apis"}[scenario]
        return reverse(panel)
    if scenario == "profile_edit":
        return reverse("finance:profile-edit", args=[profile.pk])
    if scenario == "expense_edit":
        return reverse("finance:recurring-edit", args=[profile.pk, expense.pk])
    if scenario in ("logs", "filter_focus"):
        return reverse("logs")
    if scenario == "reports_financial":
        return reverse("finance:reports-dashboard", args=[workspace.pk]) + "?period_start=2026-10-01&period_end=2026-10-31"
    if scenario == "reports":
        return reverse("relatorios")
    raise AssertionError(f"Cenário não mapeado: {scenario}")


def _assert_visible_accessibility(page, scenario):
    if scenario == "forbidden":
        return  # Resposta de erro Django separada, não tem obrigação de usar a navegação
    assert page.locator("main").count() == 1, f"Sem landmark main: {scenario}"
    assert page.locator("h1").count() >= 1, f"Sem h1: {scenario}"
    total = page.evaluate("""() => ({width:document.documentElement.scrollWidth,
        viewport:document.documentElement.clientWidth})""")
    assert total["width"] <= total["viewport"] + 2, f"Overflow horizontal: {scenario}: {total}"
    # Controles realmente navegáveis, sem aplicar regra a elementos ocultos.
    bad = page.evaluate("""() => [...document.querySelectorAll('button, a[href], input, select')]
        .filter(el => el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden')
        .filter(el => { const r=el.getBoundingClientRect(); return r.width < 1 || r.height < 1; })
        .slice(0,5).map(el => el.outerHTML.slice(0,150))""")
    assert not bad, f"Controles sem área clicável {scenario}: {bad}"
    opened = page.locator("dialog[open]")
    if opened.count():
        bounds = opened.first.bounding_box()
        assert bounds is not None, "Modal aberto sem caixa visual"
        assert bounds["x"] >= -2 and bounds["x"] + bounds["width"] <= page.viewport_size["width"] + 2, (
            f"Modal ultrapassou viewport horizontal: {bounds}")
        assert bounds["y"] >= -2 and bounds["height"] <= page.viewport_size["height"] + 2, (
            f"Modal não contém rolagem vertical: {bounds}")
    if page.viewport_size["width"] >= 1024:
        overlapping = page.evaluate("""() => {
            const side = document.querySelector('aside.sidebar');
            const main = document.querySelector('main.content');
            if (!side || !main || !side.getClientRects().length || !main.getClientRects().length) return 0;
            const a=side.getBoundingClientRect(),b=main.getBoundingClientRect();
            return Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left));
        }""")
        assert overlapping < 4, f"Sidebar invade conteúdo principal: {scenario}, {overlapping}px"


def _axe_scan(page, name):
    axe_path = Path(os.environ.get("ALECE_AXE_JS", "/tmp/alece-axe/node_modules/axe-core/axe.min.js"))
    assert axe_path.is_file(), f"axe-core indisponível, instalar versão fixada: {axe_path}"
    page.add_script_tag(path=str(axe_path))
    output = page.evaluate("""async () => await window.axe.run(document,
      {runOnly:{type:'tag', values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']}})""")
    summary = {"violations": output["violations"], "incomplete": output["incomplete"],
               "passes_count": len(output["passes"])}
    folder = EVIDENCE / "axe"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / (name + ".json")).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    assert not output["violations"], (
        f"axe-core detectou {len(output['violations'])} violações em {name}; detalhes: {folder/name}.json")


def _capture_or_compare(page, name):
    mode = os.environ.get("ALECE_VISUAL_MODE", "compare")
    target = EVIDENCE / ("candidates" if mode == "capture" else "actual") / (name + ".png")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not name.startswith(("modal_invalid__", "dropdown_open__", "filter_focus__", "button_hover__")):
        page.evaluate("document.activeElement?.blur?.()")
    # Data/hora dos logs de teste é operacional e não faz parte da geometria.
    masks = [page.locator(".logs-table .log-date")] if name.startswith("logs__") else []
    page.screenshot(path=str(target), full_page=True, animations="disabled",
                    caret="hide", mask=masks)
    if mode == "capture":
        return
    result = compare_png(BASELINES / (name + ".png"), target, EVIDENCE / "diff" / (name + ".png"))
    if not result.approved:
        EVIDENCE.joinpath("failures").mkdir(parents=True, exist_ok=True)
        (EVIDENCE / "failures" / (name + ".txt")).write_text(result.reason, encoding="utf-8")
    return result


@pytest.mark.parametrize("visual_identity", SCENARIOS, indirect=True, ids=SCENARIOS)
@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("viewport", list(VIEWPORTS))
def test_visual_scenario(visual_identity, theme, viewport):
    scenario, page, server, workspace, profile, _, expense = visual_identity
    width, height = VIEWPORTS[viewport]
    page.set_viewport_size({"width": width, "height": height})
    page.emulate_media(reduced_motion="reduce", color_scheme=theme)
    route = _route(scenario, workspace, profile, expense)
    response = page.goto(server.url + route, wait_until="domcontentloaded")
    expected_status = 403 if scenario == "forbidden" else 200
    assert response is not None and response.status == expected_status, (
        f"{scenario}: HTTP {response.status if response else 'sem resposta'}, esperado {expected_status}")
    page.evaluate("document.fonts.ready")
    # A preferência é alterada pela interface real, com persistência de sessão.
    if theme == "dark" and scenario != "forbidden":
        toggle = page.locator('[data-theme-toggle]:visible').first
        toggle.click()
        page.wait_for_function("document.documentElement.dataset.theme === 'dark'")
    if scenario == "forbidden":
        # Error HTTP has its own prefers-color-scheme CSS; incidente é aleatório
        # para correlação operacional, não deve tornar screenshot instável.
        page.locator("#incident").evaluate("e => e.textContent = 'XXXXXXXXXXXX'")
    else:
        assert page.locator("html").get_attribute("data-theme") == theme

    if scenario.startswith("message_"):
        assert page.locator(".notice[role=status]").count() > 0, "Feedback não renderizado"
    if scenario == "dropdown_open":
        trigger = page.locator("details.profile-choice:visible > summary").first
        assert trigger.count(), "Seletor de perfis não encontrado"
        trigger.click()
        assert trigger.get_attribute("aria-expanded") == "true" or page.locator("details.profile-choice[open]").count()
    if scenario == "filter_focus":
        field = page.locator(".logs-filter-field select:visible").first
        assert field.count(), "Filtro não encontrado"
        field.focus()
        assert field.evaluate("e => document.activeElement === e")
    if scenario == "button_hover":
        action = page.locator("main a.hero-shortcut:visible").first
        assert action.count(), "Ação principal não encontrada"
        action.hover()
    if scenario == "modal_invalid":
        trigger = page.locator("a.settings-modal-trigger:visible").first
        assert trigger.count(), "Disparador do modal não encontrado"
        trigger.click()
        dialog = page.locator('dialog[open]').first
        dialog.wait_for(state="visible")
        form = dialog.locator("form").first
        assert form.count(), "Modal sem formulário"
        # Força uma falha de validação client-side sem enviar dados ou salvar outra seção.
        required = form.locator("input[required]:not([type=hidden]):visible").first
        assert required.count(), "Formulário do modal sem campo obrigatório testável"
        required.fill("")
        form.locator('button[type=submit]').first.click()
        assert not required.evaluate("e => e.checkValidity()"), "Erro de validação não reproduzido"
        assert dialog.is_visible(), "Modal fechou apesar do erro de validação"
    name = f"{scenario}__{theme}__{viewport}"
    # Captura SEMPRE antes do scanner ou de asserções que podem reprovar.
    result = _capture_or_compare(page, name)
    _assert_visible_accessibility(page, scenario)
    _axe_scan(page, name)
    if result is not None:
        assert result.approved, f"Regressão visual: {name}: {result.reason}; captura em {EVIDENCE / 'actual' / (name + '.png')}"


@pytest.mark.parametrize("visual_identity", ["settings_common"], indirect=True)
def test_visual_permissions_real_http(visual_identity):
    """Usuário comum NÃO vê nem recebe HTML administrativo, independentemente de CSS."""
    scenario, page, server, *_ = visual_identity
    if scenario != "settings_common":
        pytest.skip("Contrato de permissão é específico do usuário comum")
    for route in ("configuracoes-usuarios", "configuracoes-perfis", "configuracoes-apis", "logs", "relatorios"):
        response = page.goto(server.url + reverse(route), wait_until="domcontentloaded")
        assert response is not None and response.status == 403, route


@pytest.mark.parametrize("visual_identity", ["admin_profiles"], indirect=True)
@pytest.mark.parametrize("width", [390, 1280])
def test_keyboard_modal_open_escape_and_focus_restore(visual_identity, width):
    """Fluxo funcional real: Enter abre; Escape fecha; foco retorna ao link original."""
    _, page, server, _, _, _, _ = visual_identity
    page.set_viewport_size({"width": width, "height": 844})
    response = page.goto(server.url + reverse("configuracoes-perfis"))
    assert response is not None and response.status == 200
    trigger = page.locator("a.settings-modal-trigger:visible").first
    assert trigger.count(), "Ação de edição indisponível para teclado"
    trigger.focus()
    page.keyboard.press("Enter")
    modal = page.locator("dialog[open]").first
    modal.wait_for(state="visible")
    assert modal.get_attribute("aria-labelledby") or modal.get_attribute("aria-label"), (
        "Modal sem nome acessível")
    page.keyboard.press("Escape")
    modal.wait_for(state="hidden")
    assert trigger.evaluate("el => document.activeElement === el"), "Foco não retornou ao gatilho"
