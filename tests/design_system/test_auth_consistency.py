"""Contratos estáticos da apresentação pública, sem acesso ao banco de dados."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "src/view/templates"
STATIC = ROOT / "src/view/static"


def test_authentication_pages_share_tokens_and_a_single_css_contract():
    for name in ("login", "recovery_request", "recovery_use"):
        template = (TEMPLATES / "auth" / f"{name}.html").read_text(encoding="utf-8")
        assert 'class="auth-page' in template
        assert 'finance/alece_tokens.css' in template
        assert 'finance/alece_components.css' in template
        assert 'finance/alece_auth.css' in template
        assert template.index("alece_tokens.css") < template.index("alece_auth.css")
        assert "<style>" not in template
        assert "style=" not in template
        assert 'name="csrfmiddlewaretoken"' in template or "{% csrf_token %}" in template or name == "recovery_request"


def test_auth_shared_css_uses_existing_design_tokens():
    css = (STATIC / "finance/alece_auth.css").read_text(encoding="utf-8")
    for token in (
        "--ds-color-bg", "--ds-color-surface", "--ds-color-brand",
        "--ds-control-border", "--ds-size-control", "--ds-radius-control",
        "--ds-radius-card", "--ds-color-focus",
    ):
        assert f"var({token})" in css
    assert "linear-gradient(" not in css
    assert "radial-gradient(" not in css


def test_setup_actions_and_modal_geometry_reuse_tokens():
    setup = (STATIC / "core/setup.css").read_text(encoding="utf-8")
    dialogs = (STATIC / "finance/alece_modals.css").read_text(encoding="utf-8")
    assert "background:var(--ds-color-brand)" in setup
    assert "border-radius:var(--ds-radius-control)" in setup
    assert "var(--ds-radius-dialog" in dialogs
    assert "var(--ds-size-control" in dialogs
