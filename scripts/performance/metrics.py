# SPDX-License-Identifier: GPL-3.0-only
"""Estatística de laboratório sem coleta de URLs, usuários nem valores financeiros."""
import json
from pathlib import Path
from statistics import median

MEASURES = ("server_response_ms", "dom_content_loaded_ms", "load_ms", "lcp_ms", "cls", "interaction_sample_ms")


def summary(samples):
    result = {"sample_count": len(samples)}
    for key in MEASURES:
        values = sorted(float(s[key]) for s in samples if s.get(key) is not None)
        result[key] = {
            "n": len(values),
            "median": round(median(values), 3) if values else None,
            "p75": round(values[max(0, (3 * len(values) + 3) // 4 - 1)], 3) if values else None,
        }
    return result


def compare(before, after):
    """Sem baseline comparável não apresenta ganhos ou percentuais fictícios."""
    if before.get("environment") != after.get("environment"):
        raise ValueError("Ambientes distintos; comparação numérica inválida")
    if before.get("scenario") != after.get("scenario"):
        raise ValueError("Cenários distintos")
    previous, current = summary(before["samples"]), summary(after["samples"])
    metrics = {}
    for key in MEASURES:
        a, b = previous[key]["median"], current[key]["median"]
        metrics[key] = {"before": a, "after": b, "delta": round(b - a, 3) if a is not None and b is not None else None}
    return {"scenario": after["scenario"], "before_samples": previous["sample_count"],
            "after_samples": current["sample_count"], "metrics": metrics,
            "note": "Diferenças de laboratório; não representam Core Web Vitals de campo."}


def read_run(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data.get("samples"), list) or not isinstance(data.get("environment"), dict):
        raise ValueError("Resultado de laboratório inválido")
    return data
