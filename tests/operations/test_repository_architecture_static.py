# SPDX-License-Identifier: GPL-3.0-only
"""Architecture regression checks that run even without Django or a database."""
from pathlib import Path
import ast
import unittest

ROOT = Path(__file__).resolve().parents[2]


class RepositoryArchitectureTests(unittest.TestCase):
    def test_public_removed_and_media_volume_preserved(self):
        self.assertFalse((ROOT / 'public').exists())
        compose = (ROOT / 'compose.yaml').read_text()
        self.assertIn('app_media:/app/media', compose)
        self.assertNotIn('app_media:/app/public/media', compose)

    def test_main_route_registry_has_stable_paths(self):
        web = (ROOT / 'src/web.py').read_text()
        ast.parse(web)
        for route in ('visao-geral/', 'despesas/', 'investimentos/',
                      'movimentacoes/', 'configuracoes/', 'relatorios/', 'logs/'):
            self.assertIn(f'path("{route}"', web)

    def test_startup_has_read_only_verification(self):
        starter = (ROOT / 'docker/start.sh').read_text()
        self.assertIn('python manage.py alece_startup_check', starter)
        self.assertIn('python manage.py migrate --check --noinput', starter)
        checks = (ROOT / 'src/controller/apps/core/services/startup.py').read_text()
        ast.parse(checks)
        self.assertIn("cursor.execute('SELECT 1')", checks)

    def test_no_legacy_sprint_test_files(self):
        files = list((ROOT / 'tests').rglob('test_sprint*.py'))
        self.assertEqual(files, [])

    def test_optional_local_environment_with_example_defaults(self):
        self.assertIn('ALECE_LOG_VALIDACAO=true', (ROOT / '.env.example').read_text())
        compose = (ROOT / 'compose.yaml').read_text()
        self.assertIn('path: ./.env.example\n        required: true', compose)
        self.assertIn('path: ./.env\n        required: false', compose)

    def test_web_build_context_excludes_audit_sources(self):
        ignore = (ROOT / 'docker/Dockerfile.dockerignore').read_text()
        for pattern in ('/.env', '/docs/', '/tests/', '/scripts/'):
            self.assertIn(pattern, ignore)
        self.assertTrue((ROOT / 'docker/Dockerfile.audit').is_file())
