# SPDX-License-Identifier: GPL-3.0-only
"""Capture evidence for failed browser journeys, never access real data."""
from pathlib import Path
import os
import re
import pytest


def pytest_runtest_makereport(item, call):
    if call.when == "call":
        item._alece_failed = call.excinfo is not None


@pytest.fixture
def alece_page(page, request):
    context = page.context
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    yield page
    dest = Path(os.getenv("ALECE_TEST_RESULTS", "test-results")) / "browser"
    dest.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", request.node.nodeid)[:130]
    failure = getattr(request.node, "_alece_failed", False)
    if failure:
        try:
            page.screenshot(path=str(dest / f"{safe}.png"), full_page=True)
        finally:
            context.tracing.stop(path=str(dest / f"{safe}.zip"))
    else:
        context.tracing.stop()
