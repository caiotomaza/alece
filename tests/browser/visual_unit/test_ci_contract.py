# SPDX-License-Identifier: GPL-3.0-only
"""Guardas estáticas: CI não pode promover baselines sem revisão."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]


class CIVisualContract(unittest.TestCase):
    def test_capture_is_never_baseline_promotion(self):
        source = (ROOT / "tests/browser/test_visual_regression.py").read_text(encoding="utf-8")
        self.assertIn('EVIDENCE / ("candidates" if mode == "capture" else "actual")', source)
        self.assertIn('if mode == "capture":\n        return', source)
        self.assertIn('compare_png(BASELINES / (name + ".png")', source)
        self.assertNotIn('BASELINES.mkdir(', source)

    def test_real_django_http_and_isolation(self):
        source = (ROOT / "tests/browser/test_visual_regression.py").read_text(encoding="utf-8")
        for statement in ("live_server", "client.force_login", 'ALECE_TEST_ISOLATED',
                          'db["NAME"] in ("alece_test", "test_alece_test")', "page.goto(server.url + route"):
            self.assertIn(statement, source)

    def test_ci_never_updates_reference_screenshots(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertIn("mcr.microsoft.com/playwright/python:v1.64.1-noble", workflow)
        self.assertIn("axe-core@4.14.0", workflow)
        self.assertIn("--junitxml=test-results/visual/junit.xml", workflow)
        self.assertIn("--html=test-results/visual/report.html", workflow)
        self.assertNotIn("--update-snapshots", workflow)
        self.assertNotIn("cp test-results/visual/candidates", workflow)


if __name__ == "__main__":
    unittest.main()
