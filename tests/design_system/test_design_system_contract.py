"""Contratos de Design System (sem Django, banco ou rede)."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "src/view/static/finance"
TEMPLATES = ROOT / "src/view/templates"


def test_tokens_have_two_themes_and_semantic_contract():
    css = (STATIC / "alece_tokens.css").read_text(encoding="utf-8")
    for selector in [':root, html[data-theme="light"]', 'html[data-theme="dark"]']:
        assert selector in css
    for token in ["--ds-size-control", "--ds-radius-control", "--ds-color-brand", "--ds-color-border", "--ds-color-danger", "--ds-ring", "--ds-select-chevron"]:
        assert token + ":" in css
    assert "!important" not in css


def test_color_tokens_are_not_duplicated_across_legacy_stylesheets():
    for name in ("alece.css", "alece_ui_consistency.css"):
        css = (STATIC / name).read_text(encoding="utf-8")
        assert re.search(r"--(?:bg|surface|primary)\s*:", css) is None, name
    for name in ("login.html", "recovery_use.html", "recovery_request.html"):
        assert '--bg:' not in (TEMPLATES / "auth" / name).read_text(encoding="utf-8")


def test_templates_load_stylesheets_in_stable_cascade_order():
    for name in ("finance/base.html", "core/setup.html", "auth/login.html", "auth/recovery_request.html", "auth/recovery_use.html"):
        html = (TEMPLATES / name).read_text(encoding="utf-8")
        assert 'alece_tokens.css' in html
        assert 'alece_components.css' in html
        assert html.index('alece_tokens.css') < html.index('alece_components.css')
    base = (TEMPLATES / "finance/base.html").read_text(encoding="utf-8")
    assert base.index('alece_tokens.css') < base.index('alece.css') < base.index('alece_ui_consistency.css') < base.index('alece_components.css')


def test_components_have_semantic_variants_focus_and_forced_colors():
    css = (STATIC / "alece_components.css").read_text(encoding="utf-8")
    for contract in ["ds-button--secondary", "ds-button--neutral", "ds-button--danger", ":focus-visible", "forced-colors:active", "input[type=\"checkbox\"]", "input[type=\"radio\"]", "option,optgroup", "table"]:
        assert contract in css
    assert "!important" not in css


def test_legacy_hero_visual_unchanged_and_distribution_defaults_present():
    css = (STATIC / "alece.css").read_text(encoding="utf-8")
    assert "linear-gradient(115deg,var(--hero-start),var(--hero-end))" in css
    for path in [".env.example", "compose.yaml", "LICENSE"]:
        assert (ROOT / path).is_file()


def test_design_system_css_has_valid_grammar():
    import tinycss2
    for name in ["alece_tokens.css", "alece_components.css", "alece.css", "alece_ui_consistency.css"]:
        css=(STATIC / name).read_text(encoding="utf-8")
        errors=[t for t in tinycss2.parse_stylesheet(css,skip_comments=True,skip_whitespace=True) if t.type=="error"]
        assert not errors, f"{name}: {errors}"
