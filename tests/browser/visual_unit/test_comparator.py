# SPDX-License-Identifier: GPL-3.0-only
"""Testes sem Django: falha fechada, detecção de alteração e evidências diff."""
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from scripts.visual_regression.comparator import compare_png


class BaselineComparatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.baseline = self.root / "approved.png"
        self.actual = self.root / "actual.png"
        self.diff = self.root / "evidence" / "diff.png"
        Image.new("RGB", (100, 100), (255, 255, 255)).save(self.actual)

    def test_missing_reference_is_failed_not_created(self):
        result = compare_png(self.baseline, self.actual, self.diff)
        self.assertFalse(result.approved)
        self.assertFalse(self.baseline.exists())

    def test_unchanged_pixel_map_passes_without_writing_baseline(self):
        self.baseline.write_bytes(self.actual.read_bytes())
        result = compare_png(self.baseline, self.actual, self.diff)
        self.assertTrue(result.approved)
        self.assertFalse(self.diff.exists())

    def test_relevant_change_fails_and_creates_diff(self):
        self.baseline.write_bytes(self.actual.read_bytes())
        with Image.open(self.actual) as original:
            changed = original.copy()
        for x in range(30):
            for y in range(30):
                changed.putpixel((x, y), (0, 0, 0))
        changed.save(self.actual)
        result = compare_png(self.baseline, self.actual, self.diff)
        self.assertFalse(result.approved)
        self.assertGreater(result.changed_ratio, 0.08)
        self.assertTrue(self.diff.exists())

    def test_minor_change_within_tolerance_passes(self):
        self.baseline.write_bytes(self.actual.read_bytes())
        with Image.open(self.actual) as original:
            changed = original.copy()
        changed.putpixel((0, 0), (0, 0, 0))
        changed.save(self.actual)
        self.assertTrue(compare_png(self.baseline, self.actual, self.diff).approved)

    def test_size_mismatch_fails(self):
        Image.new("RGB", (90, 100), (255, 255, 255)).save(self.baseline)
        self.assertFalse(compare_png(self.baseline, self.actual, self.diff).approved)


if __name__ == "__main__":
    unittest.main()
