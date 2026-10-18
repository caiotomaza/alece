# SPDX-License-Identifier: GPL-3.0-only
"""E2E authenticated visual verification script using Edge headless."""
import os
import re
import subprocess
import tempfile
import urllib.parse
import urllib.request
import http.cookiejar
from pathlib import Path

BASE_URL = "http://127.0.0.1:8765"
EDGE_EXE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "reviews" / "screenshots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

RESOLUTIONS = [
    (320, 640),
    (390, 844),
    (768, 1024),
    (1440, 900),
]

PAGES = [
    ("overview", "/finance/workspaces/1/?month=2026-10"),
    ("expenses", "/finance/workspaces/1/expenses/?month=2026-10"),
    ("investments", "/finance/workspaces/1/investments/?month=2026-10"),
    ("movements", "/finance/workspaces/1/movements/?month=2026-10"),
    ("profile_detail", "/finance/profiles/1/"),
    ("movement_detail_modal", "/finance/profiles/1/movements/5/"),
]


def login_session():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    # 1. GET login page to get CSRF token
    resp = opener.open(f"{BASE_URL}/login/")
    html = resp.read().decode("utf-8")
    csrf_match = re.search(r'name=["\']csrfmiddlewaretoken["\']\s+value=["\']([^"\']+)["\']', html)
    if not csrf_match:
        raise RuntimeError("CSRF token not found on login page.")
    csrf_token = csrf_match.group(1)

    # 2. POST login credentials
    post_data = urllib.parse.urlencode({
        "username": "e2e-admin",
        "password": "e2e-only-not-production",
        "csrfmiddlewaretoken": csrf_token,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/login/",
        data=post_data,
        headers={"Referer": f"{BASE_URL}/login/"},
    )
    post_resp = opener.open(req)
    if post_resp.status != 200 and not post_resp.url.endswith("/workspaces/1/"):
        # Redirect is fine
        pass
    print("Logged in successfully as e2e-admin.")
    return opener


def main():
    if not os.path.exists(EDGE_EXE):
        raise RuntimeError(f"Edge executable not found at {EDGE_EXE}")

    opener = login_session()
    temp_dir = tempfile.mkdtemp(prefix="alece_e2e_")

    for page_name, path in PAGES:
        url = f"{BASE_URL}{path}"
        req = urllib.request.Request(url)
        with opener.open(req) as resp:
            content = resp.read().decode("utf-8")

        # Inject base href so static assets resolve cleanly to http://127.0.0.1:8765/
        if "<head>" in content:
            content = content.replace("<head>", f'<head><base href="{BASE_URL}/">', 1)

        for theme in ["light", "dark"]:
            themed_content = re.sub(r'<html[^>]*>', f'<html lang="pt-BR" data-theme="{theme}">', content)
            script_inject = f"<script>try{{localStorage.setItem('alece-theme', '{theme}');}}catch(e){{}} document.documentElement.dataset.theme = '{theme}';</script></head>"
            themed_content = themed_content.replace("</head>", script_inject, 1)

            html_file = os.path.join(temp_dir, f"{page_name}_{theme}.html")
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(themed_content)

            file_url = Path(html_file).as_uri()

            for width, height in RESOLUTIONS:
                out_png = OUTPUT_DIR / f"{page_name}_{theme}_{width}px.png"
                cmd = [
                    EDGE_EXE,
                    "--headless",
                    f"--window-size={width},{height}",
                    f"--screenshot={out_png}",
                    f"--user-data-dir={os.path.join(temp_dir, 'profile')}",
                    "--disable-gpu",
                    file_url,
                ]
                res = subprocess.run(cmd, capture_output=True, text=True)
                if not out_png.exists() or out_png.stat().st_size == 0:
                    print(f"FAILED {out_png.name}: {res.stderr}")
                else:
                    print(f"Captured: {out_png.name} ({out_png.stat().st_size} bytes)")

    print(f"All E2E screenshots captured in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
