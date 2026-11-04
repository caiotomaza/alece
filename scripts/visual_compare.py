"""Capture measured, same-viewport comparisons of the ALECE reference and app.

Run only against the isolated audit database and loopback servers. The reference
contains historical sample values, so keep baseline captures out of Git.
"""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright


SIZES = ((320, 640), (390, 844), (768, 1024), (1440, 900))
PAGES = ("overview", "expenses", "investments", "movements", "settings")
ROUTES = {
    "overview": "",
    "expenses": "expenses/",
    "investments": "investments/",
    "movements": "movements/",
    "settings": "profiles/",
}


def audit_session():
    """Create a session for an existing synthetic user without handling a password."""
    if os.environ.get("ALECE_DB_NAME") != "alece_audit":
        raise SystemExit("Visual capture requires the isolated audit database")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "controller"))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()
    from django.contrib.auth import get_user_model
    from django.test import Client
    from apps.finance.models import FinancialProfile, WorkspaceMembership

    user = get_user_model().objects.get(username=os.environ["ALECE_VISUAL_USER"])
    membership = WorkspaceMembership.objects.filter(user=user, role="admin").order_by("pk").first()
    if membership is None:
        raise RuntimeError("A synthetic workspace administrator is required")
    client = Client()
    client.force_login(user)
    ids = dict(FinancialProfile.objects.filter(
        workspace_id=membership.workspace_id, name__in=("Visual completo", "Visual vazio"),
    ).values_list("name", "pk"))
    return client.cookies["sessionid"].value, membership.workspace_id, ids


def metrics(page):
    return page.evaluate("""() => {
      const rect = (selector) => {
        const el = document.querySelector(selector);
        if (!el || getComputedStyle(el).display === 'none') return null;
        const box = el.getBoundingClientRect();
        return {x: Math.round(box.x), y: Math.round(box.y),
                width: Math.round(box.width), height: Math.round(box.height)};
      };
      return {
        width: innerWidth, height: innerHeight, dpr: devicePixelRatio,
        scale: visualViewport?.scale ?? null,
        fontStatus: document.fonts.status,
        fontFamily: getComputedStyle(document.body).fontFamily,
        theme: document.documentElement.dataset.theme,
        scrollWidth: document.documentElement.scrollWidth,
        sidebar: rect('.sidebar'), content: rect('.content'),
        intro: rect('.page.is-visible .intro'), hero: rect('.page.is-visible .hero'),
        headings: [...document.querySelectorAll('main h1,main h2,main h3')]
          .filter(el => el.getClientRects().length)
          .map(el => el.textContent.trim()).slice(0, 24)
      };
    }""")


def checked_capture(page, width, height, theme):
    page.evaluate("() => document.fonts.ready.then(() => true)")
    actual = metrics(page)
    if (actual["width"], actual["height"]) != (width, height):
        raise RuntimeError(f"Viewport mismatch: expected {(width, height)}, got {actual}")
    if actual["dpr"] != 1 or actual["scale"] != 1:
        raise RuntimeError(f"Scale mismatch: {actual}")
    if actual["fontStatus"] != "loaded" or actual["theme"] != theme:
        raise RuntimeError(f"Font/theme mismatch: {actual}")
    return page.screenshot(full_page=False, animations="disabled"), actual


def comparison(left_png, right_png, label):
    left = Image.open(io.BytesIO(left_png)).convert("RGB")
    right = Image.open(io.BytesIO(right_png)).convert("RGB")
    width = left.width + right.width
    image = Image.new("RGB", (width, max(left.height, right.height) + 28), "white")
    draw = ImageDraw.Draw(image)
    draw.text((8, 8), f"PROTOTYPE | {label}", fill="#17261D")
    draw.text((left.width + 8, 8), f"DJANGO | {label}", fill="#17261D")
    image.paste(left, (0, 28))
    image.paste(right, (left.width, 28))
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference", default="http://127.0.0.1:8765/")
    parser.add_argument("--application", default="http://127.0.0.1:8003/")
    parser.add_argument("--state", choices=("baseline", "filled", "empty"), default="baseline")
    args = parser.parse_args()
    cookie, workspace_id, profile_ids = audit_session()
    selected_profile = {
        "baseline": None, "filled": profile_ids.get("Visual completo"),
        "empty": profile_ids.get("Visual vazio"),
    }[args.state]
    if args.state != "baseline" and selected_profile is None:
        raise RuntimeError("Run scripts/seed_visual_audit.py against the isolated database")
    args.output.mkdir(parents=True, exist_ok=True)
    observations = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        for width, height in SIZES:
            for theme in ("light", "dark"):
                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    device_scale_factor=1, color_scheme="light", reduced_motion="reduce",
                )
                context.add_cookies([{
                    "name": "sessionid", "value": cookie, "url": args.application,
                }])
                prototype = context.new_page()
                application = context.new_page()
                errors = {"prototype": [], "application": []}
                prototype.on("pageerror", lambda error: errors["prototype"].append(str(error)))
                application.on("pageerror", lambda error: errors["application"].append(str(error)))
                if prototype.goto(args.reference).status != 200:
                    raise RuntimeError("Reference did not load")
                if args.state != "baseline":
                    prototype.locator("#finance-profile-toggle:visible").click()
                    prototype.locator(
                        f"#finance-profile-menu .profile-chip[data-scope='{'caio' if args.state == 'filled' else 'mel'}']"
                    ).click()
                selection = f"?profiles={selected_profile}" if selected_profile else ""
                if application.goto(
                    f"{args.application}finance/workspaces/{workspace_id}/{selection}"
                ).status != 200:
                    raise RuntimeError("Application did not load")
                if theme == "dark":
                    prototype.locator("#theme-toggle:visible, #mobile-theme-toggle:visible").click()
                    application.locator("[data-theme-toggle]:visible").click()
                for section in PAGES:
                    if section != "overview":
                        prototype.locator(f"button[data-page='{section}']:visible").first.click()
                    prototype.locator(f"#page-{section}.is-visible").wait_for()
                    application.goto(
                        f"{args.application}finance/workspaces/{workspace_id}/{ROUTES[section]}"
                        f"{selection if section != 'settings' else ''}"
                    )
                    prototype.wait_for_timeout(220)
                    application.wait_for_timeout(220)
                    ref_png, ref_metrics = checked_capture(prototype, width, height, theme)
                    app_png, app_metrics = checked_capture(application, width, height, theme)
                    label = f"{section} {width}x{height} {theme}"
                    data = comparison(ref_png, app_png, label)
                    full_data = comparison(
                        prototype.screenshot(full_page=True, animations="disabled"),
                        application.screenshot(full_page=True, animations="disabled"), label,
                    )
                    folder = args.output / section
                    folder.mkdir(exist_ok=True)
                    path = folder / f"{width}x{height}_{theme}.png"
                    path.write_bytes(data)
                    full_path = folder / f"{width}x{height}_{theme}_full.png"
                    full_path.write_bytes(full_data)
                    observations.append({
                        "page": section, "state": args.state, "width": width, "height": height,
                        "theme": theme, "path": str(path),
                        "sha256": hashlib.sha256(data).hexdigest(),
                        "full_path": str(full_path),
                        "full_sha256": hashlib.sha256(full_data).hexdigest(),
                        "reference": ref_metrics, "application": app_metrics,
                        "errors": {key: list(value) for key, value in errors.items()},
                    })
                    print(f"captured {label}", flush=True)
                context.close()
        browser.close()

    (args.output / "measurements.json").write_text(
        json.dumps(observations, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    print(f"scenarios={len(observations)}", flush=True)


if __name__ == "__main__":
    main()
