# SPDX-License-Identifier: GPL-3.0-only
"""Comparação determinística de PNGs produzidos pelo Playwright.

Não usa aproximação estrutural ou aprovação implícita; sempre escreve um PNG
atual e, em divergências, uma evidência anotada e uma descrição legível.
"""
from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageChops


@dataclass(frozen=True)
class Comparison:
    approved: bool
    changed_ratio: float
    reason: str


def compare_png(reference: Path, actual: Path, diff: Path, *, allowed_ratio: float = 0.001,
                channel_tolerance: int = 12) -> Comparison:
    if not 0 <= allowed_ratio < 1 or not 0 <= channel_tolerance <= 255:
        raise ValueError("Limites inválidos para comparação visual")
    if not reference.is_file():
        return Comparison(False, 1.0, f"Baseline ausente: {reference}. Rever e aprovar manualmente.")
    with Image.open(reference) as source, Image.open(actual) as candidate:
        old, new = source.convert("RGB"), candidate.convert("RGB")
        if old.size != new.size:
            return Comparison(False, 1.0, f"Dimensões diferentes: {old.size} versus {new.size}")
        delta = ImageChops.difference(old, new)
        # Maior diferença de qualquer canal, com tolerância explícita por canal.
        r, g, b = delta.split()
        change = ImageChops.lighter(ImageChops.lighter(r, g), b)
        mask = change.point(lambda x: 255 if x > channel_tolerance else 0)
        changed = mask.histogram()[255]
        ratio = changed / (old.width * old.height)
        if ratio > allowed_ratio:
            diff.parent.mkdir(parents=True, exist_ok=True)
            # O vermelho é somente anotação da evidência, não alteração da baseline.
            overlay = Image.new("RGB", new.size, (225, 30, 50))
            marked = Image.composite(overlay, new, mask)
            marked.save(diff)
            return Comparison(False, ratio, f"Alterados {changed} pixels ({ratio:.3%}); limite {allowed_ratio:.3%}")
        return Comparison(True, ratio, f"Alterados {changed} pixels ({ratio:.3%}) dentro do limite")
