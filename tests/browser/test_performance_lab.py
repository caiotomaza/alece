# SPDX-License-Identifier: GPL-3.0-only
"""Laboratório Playwright real; não é RUM nem envia telemetria externa."""
import json
import os
from pathlib import Path
import platform

import pytest
from test_visual_regression import _route, visual_identity  # noqa: F401 — fixture PostgreSQL

pytestmark = [pytest.mark.browser]

# Reduzimos volume sem perder os destinos fundamentais. Dados são sintéticos.
SCENARIOS = (
    "overview_empty", "overview_filled", "expenses_filled", "investments_filled",
    "movements_filled", "settings_common", "reports_financial",
    "import_upload", "admin_users", "logs",
)
SCRIPT = r"""(() => {
  window.__aleceLab = {lcp: null, cls: 0, interactions: []};
  const observe = (type, fn, opts={}) => {
    try { new PerformanceObserver(list => list.getEntries().forEach(fn))
      .observe({type, buffered:true, ...opts}); } catch (_) {}
  };
  observe('largest-contentful-paint', entry => {window.__aleceLab.lcp = entry.startTime;});
  observe('layout-shift', entry => {
    if (!entry.hadRecentInput) window.__aleceLab.cls += entry.value;
  });
  observe('event', entry => {
    if (entry.interactionId && entry.duration) window.__aleceLab.interactions.push(entry.duration);
  }, {durationThreshold:16});
})();"""


def _metrics(page, response):
    # Mede renderização da navegação real. Não lê conteúdo do DOM, cookies nem dados financeiros.
    timing = page.evaluate("""() => {
      const n = performance.getEntriesByType('navigation')[0];
      if (!n) return null;
      return {server_response_ms:n.responseStart, dom_content_loaded_ms:n.domContentLoadedEventEnd,
              load_ms:n.loadEventEnd || null,
              lcp_ms:window.__aleceLab?.lcp ?? null,
              cls:window.__aleceLab?.cls ?? null,
              interaction_sample_ms:window.__aleceLab?.interactions.length ?
                Math.max(...window.__aleceLab.interactions) : null};
    }""")
    assert response is not None and response.status == 200, "Falha HTTP na medição"
    assert timing and timing["server_response_ms"] >= 0
    return timing


@pytest.mark.parametrize("visual_identity", SCENARIOS, indirect=True, ids=SCENARIOS)
@pytest.mark.parametrize("viewport", [(390, 844), (1280, 800)], ids=["mobile", "desktop"])
def test_isolated_lab(visual_identity, viewport):
    # Fixture original exige explicitamente PostgreSQL efêmero alece_test e não produção.
    scenario, page, server, workspace, profile, _, expense = visual_identity
    page.set_viewport_size({"width":viewport[0],"height":viewport[1]})
    page.emulate_media(reduced_motion="reduce")
    page.add_init_script(SCRIPT)
    route = _route(scenario, workspace, profile, expense)
    url = server.url + route
    env = {
        "browser": page.context.browser.version,
        "engine": "chromium", "viewport_css": list(viewport), "reduced_motion": "reduce",
        "python": platform.python_version(), "os": platform.platform(),
        "db": "PostgreSQL isolado (alece_test)",
        "mode": "laboratório; sem throttling de rede; cache HTTP preservado nas repetições",
    }
    samples = []
    for i in range(5):
        response = page.goto(url, wait_until="load")
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(200)
        samples.append(_metrics(page, response))
    payload = {"scenario": scenario, "environment": env, "samples": samples,
               "note": "INP de campo NÃO aferido. interaction_sample_ms só existe se houve interação observável."}
    output = Path(os.environ.get("ALECE_TEST_RESULTS", "test-results")) / "performance" / "runs"
    output.mkdir(parents=True, exist_ok=True)
    (output / f"{scenario}__{viewport[0]}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert len(samples) == 5
