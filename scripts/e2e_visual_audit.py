"""Real-browser journeys against synthetic data in the isolated audit stack."""
import sys

import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from playwright.sync_api import sync_playwright

from visual_compare import SIZES, audit_session


def prepare_reader(workspace, profile):
    from django.contrib.auth import get_user_model
    from django.test import Client

    from apps.finance.models import ProfileGrant, WorkspaceMembership

    user, created = get_user_model().objects.get_or_create(username="visual_e2e_reader")
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    member, _ = WorkspaceMembership.objects.get_or_create(
        workspace=workspace, user=user, defaults={"role": "common"},
    )
    grant, _ = ProfileGrant.objects.get_or_create(membership=member, profile=profile)
    grant.can_view = True
    grant.can_edit = False
    grant.overview_level = "view"
    grant.accounts_level = "view"
    grant.expenses_level = "view"
    grant.investments_level = "view"
    grant.movements_level = "view"
    grant.save()
    client = Client()
    client.force_login(user)
    return client.cookies["sessionid"].value, grant


def main():
    if os.environ.get("ALECE_DB_NAME") != "alece_audit":
        raise SystemExit("E2E requires the isolated audit database")
    cookie, workspace_id, profile_ids = audit_session()
    filled_id = profile_ids["Visual completo"]
    empty_id = profile_ids["Visual vazio"]
    from apps.finance.models import FinancialProfile, TransactionBatch, UnexpectedExpense, Workspace
    from django.urls import reverse

    workspace = Workspace.objects.get(pk=workspace_id)
    profile = FinancialProfile.objects.get(pk=filled_id)
    base = "http://127.0.0.1:8003"
    output = Path(os.environ.get("ALECE_E2E_OUTPUT", str(Path(os.getenv("TEMP", ".")) / "alece-e2e")))
    output.mkdir(parents=True, exist_ok=True)
    events = []
    before_ledger = TransactionBatch.objects.filter(profile=profile).count()
    expense_exists = UnexpectedExpense.objects.filter(
        profile=profile, name="Teste E2E de interface",
    ).exists()
    reader_cookie, grant = prepare_reader(workspace, profile)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        for width, height in SIZES:
            for theme in ("light", "dark"):
                context = browser.new_context(
                    viewport={"width": width, "height": height}, device_scale_factor=1,
                    color_scheme="light", reduced_motion="reduce",
                )
                context.add_cookies([{"name": "sessionid", "value": cookie, "url": base}])
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                expenses = f"{base}/finance/workspaces/{workspace_id}/expenses/?profiles={filled_id}"
                assert page.goto(expenses).status == 200
                assert page.get_by_text("Reparo de teste").count() >= 1
                if theme == "dark":
                    page.locator("[data-theme-toggle]:visible").click()
                    page.reload()
                assert page.locator("html").get_attribute("data-theme") == theme
                if width == 320 and theme == "light":
                    profile_menu = page.locator("summary.sidebar-profile-toggle:visible").first
                    profile_menu.click()
                    page.locator(f".mobile-profile-slot a.profile-chip[href$='profiles={empty_id}']").click()
                    assert page.get_by_text("Reparo de teste").count() == 0
                    page.goto(expenses)
                    month_input = page.locator(".month-ref-control input[name='month']")
                    month_input.fill("2025-01")
                    month_input.press("Enter")
                    assert "month=2025-01" in page.url
                    page.goto(expenses)
                page.get_by_role("link", name="Adicionar despesa imprevisível").click()
                dialog = page.locator("dialog[open]")
                dialog.wait_for()
                assert page.url == expenses, "The form replaced its background page"
                assert dialog.get_by_role("button", name="Salvar e fechar").count() == 1
                assert dialog.get_by_role("link", name="Cancelar").count() == 1
                if width == 320 and theme == "light" and not expense_exists:
                    dialog.locator("#id_name").fill("Teste E2E de interface")
                    dialog.locator("#id_amount").fill("17.25")
                    dialog.get_by_role("button", name="Salvar e fechar").click()
                    page.wait_for_url(f"{base}/finance/workspaces/{workspace_id}/expenses/")
                    expense_exists = True
                    page.goto(expenses)
                    page.reload()
                    assert page.get_by_text("Teste E2E de interface").count() >= 1
                    page.get_by_role("link", name="Adicionar despesa imprevisível").click()
                    dialog = page.locator("dialog[open]")
                geometry = page.evaluate("""() => ({width:innerWidth, scroll:document.documentElement.scrollWidth,
                  dialog:(() => {let r=document.querySelector('dialog[open]').getBoundingClientRect();
                    return {left:r.left,right:r.right,bottom:r.bottom}})()})""")
                assert geometry["width"] == width and geometry["scroll"] <= width
                assert geometry["dialog"]["left"] >= 0 and geometry["dialog"]["right"] <= width
                assert geometry["dialog"]["bottom"] <= height
                screenshot = output / f"modal_{width}x{height}_{theme}.png"
                page.screenshot(path=str(screenshot), animations="disabled")
                dialog.get_by_role("link", name="Cancelar").click()
                assert page.url == expenses and page.locator("dialog[open]").count() == 0
                page.goto(f"{base}/finance/workspaces/{workspace_id}/expenses/?profiles={empty_id}")
                assert page.get_by_text("Reparo de teste").count() == 0
                assert not errors, errors
                events.append({"width": width, "height": height, "theme": theme,
                               "modal": str(screenshot), "javascript_errors": 0,
                               "global_overflow": False})
                context.close()
        context = browser.new_context()
        context.add_cookies([{"name": "sessionid", "value": reader_cookie, "url": base}])
        reader = context.new_page()
        reader_url = f"{base}/finance/workspaces/{workspace_id}/expenses/?profiles={filled_id}"
        assert reader.goto(reader_url).status == 200
        assert reader.get_by_text("Reparo de teste").count() >= 1
        assert reader.get_by_role("link", name="Adicionar despesa imprevisível").count() == 0
        assert reader.goto(f"{base}/finance/profiles/{filled_id}/unexpected/new/").status == 403
        assert reader.goto(f"{base}{reverse('core:system-logs-list')}").status == 403
        grant.expenses_level = "none"
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(grant.save, update_fields=["expenses_level"]).result()
        assert reader.goto(reader_url).status in (200, 400)
        assert reader.get_by_text("Reparo de teste").count() == 0
        assert reader.goto(f"{base}/finance/profiles/{filled_id}/unexpected/new/").status == 403
        context.close()
        context = browser.new_context()
        context.add_cookies([{"name": "sessionid", "value": cookie, "url": base}])
        administrator = context.new_page()
        assert administrator.goto(f"{base}{reverse('core:system-logs-list')}").status == 200
        context.close()
        browser.close()

    after_ledger = TransactionBatch.objects.filter(profile=profile).count()
    assert after_ledger == before_ledger, "Registration changed the ledger"
    assert UnexpectedExpense.objects.filter(profile=profile, name="Teste E2E de interface").exists()
    (output / "results.json").write_text(json.dumps(events, indent=2), encoding="utf-8")
    print(f"modal_scenarios={len(events)} persistence=ok revocation=ok ledger_unchanged=ok")


if __name__ == "__main__":
    main()
