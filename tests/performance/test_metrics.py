# SPDX-License-Identifier: GPL-3.0-only
import pytest
from scripts.performance.metrics import summary, compare


def test_summary_marks_unavailable_metrics_not_zero():
    s = summary([{"load_ms": 120, "lcp_ms": None}, {"load_ms": 100, "lcp_ms": None}])
    assert s["lcp_ms"]["median"] is None
    assert s["lcp_ms"]["n"] == 0
    assert s["load_ms"]["median"] == 110


def test_comparison_does_not_invent_gain():
    baseline = {"scenario": "overview", "environment": {"browser":"fixed"},
                "samples": [{"lcp_ms": 200.0}, {"lcp_ms": 100.0}]}
    changed = {**baseline, "samples": [{"lcp_ms": 90.0}, {"lcp_ms": 110.0}]}
    r = compare(baseline, changed)
    assert r["metrics"]["lcp_ms"] == {"before":150.0,"after":100.0,"delta":-50.0}
    assert r["metrics"]["interaction_sample_ms"]["delta"] is None


def test_reject_incomparable_environments():
    a = {"scenario":"overview","environment":{"browser":"A"},"samples":[]}
    b = {**a, "environment":{"browser":"B"}}
    with pytest.raises(ValueError, match="Ambientes distintos"):
        compare(a,b)
