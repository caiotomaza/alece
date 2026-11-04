"""Structural regression tests for packaging and first-run presentation.

Does not require Django, a network connection or PostgreSQL.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class RepositoryStructureTests(unittest.TestCase):
    def test_compose_project_named_alece(self):
        compose = (ROOT / 'compose.yaml').read_text(encoding='utf-8')
        self.assertRegex(compose, r'(?m)^name: alece$')
        self.assertNotIn('name: alece-mvc', compose)

    def test_volumes_do_not_reuse_old_alece_dbdata(self):
        compose = (ROOT / 'compose.yaml').read_text(encoding='utf-8')
        self.assertRegex(compose, r'(?m)^  app_pgdata:$')
        self.assertNotRegex(compose, r'(?m)^  dbdata:$')

    def test_requirements_moved_and_referenced(self):
        self.assertFalse((ROOT / 'requirements').exists())
        self.assertTrue((ROOT / 'src/requirements/production.lock').is_file())
        self.assertTrue((ROOT / 'src/requirements/development.lock').is_file())
        dockerfile = (ROOT / 'docker/Dockerfile').read_text(encoding='utf-8')
        self.assertIn('COPY src/requirements/ /app/src/requirements/', dockerfile)
        self.assertIn('-r src/requirements/production.lock', dockerfile)
        ci = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')
        self.assertIn('src/requirements/development.lock', ci)

    def test_reference_directory_removed_but_prototype_preserved(self):
        self.assertFalse((ROOT / 'reference').exists())
        self.assertTrue((ROOT / 'docs/prototype/ALECE_Prototipo_Visual_v1.32.1.html').is_file())

    def test_setup_template_contains_user_passwords_and_optional_email(self):
        html = (ROOT / 'src/view/templates/core/setup.html').read_text(encoding='utf-8')
        for field in ('username', 'email', 'password1', 'password2'):
            self.assertEqual(html.count('{{ form.' + field + ' }}'), 1)
        self.assertEqual(html.count('class="setup-field"'), 4)
        self.assertNotIn('form.token', html)
        self.assertNotIn('form.workspace_name', html)
        self.assertNotIn('form.profile_name', html)
        self.assertIn("'core/setup.css'", html)
        self.assertIn('Criar Administrador', html)

    def test_setup_inputs_full_width_and_themed(self):
        css = (ROOT / 'src/view/static/core/setup.css').read_text(encoding='utf-8')
        self.assertIn('width:100%;max-width:100%', css)
        self.assertIn('grid-template-columns:minmax(0,1fr)', css)
        self.assertTrue('var(--ds-control-surface)' in css or 'var(--field)' in css)
        self.assertIn('@media(max-width:520px)', css)
        forms = (ROOT / 'src/controller/apps/core/forms.py').read_text(encoding='utf-8')
        form = forms.split('class BootstrapSetupForm(', 1)[1].split('class UserManagementForm(', 1)[0]
        self.assertEqual(form.count('"class": "setup-input"'), 4)


if __name__ == '__main__':
    unittest.main()
