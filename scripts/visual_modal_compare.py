"""Capture real reference and Django dialogs at exact viewport sizes."""

import hashlib
import json
import os
from pathlib import Path
import sys

from playwright.sync_api import sync_playwright

from visual_compare import SIZES, audit_session, checked_capture, comparison


SCENARIOS = (
    ("overview", "#income-edit", "Editar renda mensal"),
    ("overview", "#account-add", "Adicionar conta"),
    ("expenses", "#fixed-add", "Adicionar despesa previsível"),
    ("expenses", "#variable-add", "Adicionar despesa imprevisível"),
    ("investments", "#investment-add", "Adicionar investimento"),
    ("movements", "#movement-add", "Nova transferência"),
)


def main():
    if os.environ.get("ALECE_DB_NAME") != "alece_audit":
        raise SystemExit("Only the isolated audit database is permitted")
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=True)
    cookie, workspace_id, profile_ids = audit_session()
    profile_id = profile_ids["Visual completo"]
    observations = []
    base = "http://127.0.0.1:8003/"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        for width, height in SIZES:
            for theme in ("light", "dark"):
                context = browser.new_context(
                    viewport={"width": width, "height": height}, device_scale_factor=1,
                    color_scheme="light", reduced_motion="reduce",
                )
                context.add_cookies([{"name": "sessionid", "value": cookie, "url": base}])
                for section, ref_trigger, app_label in SCENARIOS:
                    reference = context.new_page()
                    application = context.new_page()
                    ref_errors = []
                    app_errors = []
                    reference.on("pageerror", lambda error: ref_errors.append(str(error)))
                    application.on("pageerror", lambda error: app_errors.append(str(error)))
                    assert reference.goto("http://127.0.0.1:8765/").status == 200
                    reference.locator("#finance-profile-toggle:visible").click()
                    reference.locator("#finance-profile-menu .profile-chip[data-scope='caio']").click()
                    if section != "overview":
                        reference.locator(f"button[data-page='{section}']:visible").first.click()
                    assert application.goto(
                        f"{base}finance/workspaces/{workspace_id}/{'' if section == 'overview' else section + '/'}?profiles={profile_id}"
                    ).status == 200
                    if theme == "dark" and reference.locator("html").get_attribute("data-theme") != "dark":
                        reference.locator("#theme-toggle:visible, #mobile-theme-toggle:visible").click()
                    if theme == "dark" and application.locator("html").get_attribute("data-theme") != "dark":
                        application.locator("[data-theme-toggle]:visible").click()
                    reference.locator(ref_trigger).click()
                    application.get_by_role("link", name=app_label).click()
                    reference.locator("dialog[open]").first.wait_for()
                    application.locator("dialog[open]").first.wait_for()
                    ref_png, ref_metrics = checked_capture(reference, width, height, theme)
                    app_png, app_metrics = checked_capture(application, width, height, theme)
                    ref_box = reference.locator("dialog[open]").first.bounding_box()
                    app_box = application.locator("dialog[open]").first.bounding_box()
                    name = ref_trigger.lstrip("#")
                    path = output / f"{name}_{width}x{height}_{theme}.png"
                    image = comparison(ref_png, app_png, f"{name} {width}x{height} {theme}")
                    path.write_bytes(image)
                    observations.append({
                        "modal": name, "width": width, "height": height, "theme": theme,
                        "path": str(path), "sha256": hashlib.sha256(image).hexdigest(),
                        "reference_dialog": ref_box, "application_dialog": app_box,
                        "reference_viewport": ref_metrics, "application_viewport": app_metrics,
                        "reference_errors": ref_errors, "application_errors": app_errors,
                    })
                    reference.close()
                    application.close()
                    print(f"captured {name} {width}x{height} {theme}", flush=True)
                context.close()
        browser.close()
    (output / "measurements.json").write_text(
        json.dumps(observations, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    print(f"modal_scenarios={len(observations)}", flush=True)


if __name__ == "__main__":
    main()
