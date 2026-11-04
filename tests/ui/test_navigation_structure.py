"""Fast packaging checks requiring no running Django/PostgreSQL."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class NavigationStructureTests(unittest.TestCase):
    def test_canonical_urls_are_registered_without_ids(self):
        urls = (ROOT / 'src/web.py').read_text('utf-8')
        for slug in ('visao-geral', 'despesas', 'investimentos', 'movimentacoes', 'configuracoes'):
            self.assertIn(f'path("{slug}/"', urls)
        self.assertIn('path("preferencias/tema/"', urls)

    def test_navigation_only_links_to_short_urls(self):
        html = (ROOT / 'src/view/templates/finance/base.html').read_text('utf-8')
        self.assertNotIn("{% url 'finance:overview'", html)
        self.assertNotIn("{% url 'finance:profile-list'", html)
        self.assertIn('https://caiotomaza.github.io/projetos/alece/', html)
        self.assertNotIn('class="account-link"', html)

    def test_security_links_only_in_settings(self):
        settings = (ROOT / 'src/view/templates/core/settings_dashboard.html').read_text('utf-8')
        self.assertNotIn('<h2>Aparência</h2>', settings)
        self.assertIn("{% url 'password_change' %}", settings)
        self.assertIn("{% url 'recovery_generate' %}", settings)

    def test_theme_is_user_owned_and_database_authoritative(self):
        model = (ROOT / 'src/controller/apps/core/models.py').read_text('utf-8')
        prefs = (ROOT / 'src/controller/apps/core/preferences.py').read_text('utf-8')
        processor = (ROOT / 'src/controller/apps/core/context_processors.py').read_text('utf-8')
        js = (ROOT / 'src/view/static/finance/alece.js').read_text('utf-8')
        self.assertIn('theme = models.CharField', model)
        self.assertIn('UserProfile.objects.update_or_create(user=request.user', prefs)
        self.assertIn("choice = UserProfile.objects.filter(user_id=request.user.pk)", processor)
        self.assertIn('alece-theme-user-', js)
        self.assertIn('X-CSRFToken', js)


if __name__ == '__main__':
    unittest.main()
