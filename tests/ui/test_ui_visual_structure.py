"""Checks that do not need Django/DB for ALECE's front-end regression contract."""
from pathlib import Path
from xml.etree import ElementTree
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / "src/view/templates"
STATIC = ROOT / "src/view/static/finance"

class VisualConsistencyTests(unittest.TestCase):
    def test_same_svg_favicon_across_application(self):
        svg = STATIC / "favicon.svg"
        self.assertEqual(ElementTree.parse(svg).getroot().tag.split("}")[-1], "svg")
        base = (TEMPLATES / "finance/base.html").read_text()
        self.assertIn("finance/favicon.svg", base)
        self.assertIn('<img class="brandmark"', base)
        for page in (TEMPLATES / "auth").glob("*.html"):
            page_source = page.read_text()
            self.assertTrue(
                "finance/favicon.svg" in page_source or
                '{% extends "finance/base.html" %}' in page_source,
                page.name,
            )

    def test_settings_roles_and_shortcut_windows(self):
        text = (TEMPLATES / "core/settings_dashboard.html").read_text()
        self.assertIn("{% if is_workspace_admin %}", text)
        for route in ("configuracoes-usuarios", "configuracoes-perfis", "configuracoes-apis", "logs", "relatorios"):
            self.assertIn("{% url '" + route + "' %}", text)
        self.assertIn('class="settings-board"', text)
        self.assertIn('settings-modal-trigger', text)  # pessoais continuam em pop-ups
        for route in ("configuracoes-usuarios", "configuracoes-perfis", "configuracoes-apis"):
            self.assertIn("class=\"settings-action-card\" href=\"{% url '" + route + "' %}\"", text)
        self.assertNotIn("<table", text)
        admin = (TEMPLATES / "core/settings_admin_panel.html").read_text()
        self.assertIn('settings-management-intro', admin)
        self.assertNotIn('data-dialog-content', admin)
        self.assertNotIn('data-edit-dialog', admin)
        self.assertIn('settings-table-scroll', admin)
        self.assertIn('href="#i-edit"', admin)

    def test_settings_templates_balanced(self):
        text = (TEMPLATES / "core/settings_dashboard.html").read_text()
        stack = []
        starters = ("if", "for", "with", "block")
        for body in re.findall(r"\{%\s*(.*?)\s*%\}", text, flags=re.S):
            tag = body.split()[0]
            if tag in starters: stack.append(tag)
            elif tag.startswith("end") and tag[3:] in starters:
                self.assertTrue(stack, tag)
                self.assertEqual(stack.pop(), tag[3:])
        self.assertFalse(stack, stack)

    def test_modal_actions_preserve_django_forms(self):
        for name in ("settings_form.html", "user_edit.html", "user_management.html", "user_password_reset.html"):
            text = (TEMPLATES / "core" / name).read_text()
            self.assertIn("data-dialog-content", text)
            self.assertIn('method="post"', text)
            self.assertIn('{% csrf_token %}', text)
        js = (STATIC / "alece.js").read_text()
        self.assertIn("a.settings-modal-trigger", js)
        self.assertIn("overlay.dataset.settingsModal", js)
        self.assertIn("new FormData(postingForm)", js)

    def test_checkbox_and_responsive_css(self):
        style = (STATIC / "alece_ui_consistency.css").read_text()
        self.assertIn('input[type="checkbox"]', style)
        self.assertIn("accent-color", style)
        self.assertIn("@media(max-width:700px)", style)
        self.assertIn(".settings-board", style)
        self.assertIn("data-label", style)
        object_form = (TEMPLATES / "finance/object_form.html").read_text()
        self.assertIn('widget.input_type == \'checkbox\'', object_form)
        self.assertIn("checkbox-control", object_form)

    def test_browser_tab_omits_workspace_profile_name(self):
        overview = (TEMPLATES / "finance/workspace_page.html").read_text().split("{% endblock %}")[0]
        self.assertNotIn("workspace.name", overview)
        profile = (TEMPLATES / "finance/profile_detail.html").read_text().split("{% endblock %}")[0]
        self.assertNotIn("profile.name", profile)

if __name__ == "__main__":
    unittest.main()
