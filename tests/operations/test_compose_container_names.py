"""Checks of the declared container identities (no Docker needed)."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ContainerNamingTests(unittest.TestCase):
    def test_fixed_container_names_match_existing_services(self):
        text = (ROOT / 'compose.yaml').read_text(encoding='utf-8')
        import re
        for service, name in (('web', 'alece_web'), ('db', 'alece_db'),
                              ('secrets-init', 'alece_secrets_init')):
            with self.subTest(service=service):
                self.assertRegex(text, rf'(?m)^  {service}:\n    container_name: {name}$')
        self.assertEqual(text.count('container_name:'), 3)

    def test_persisted_volumes_and_dependencies_preserved(self):
        text = (ROOT / 'compose.yaml').read_text(encoding='utf-8')
        for field in ('app_pgdata:', 'app_secrets:', 'app_media:',
                      'service_completed_successfully', 'service_healthy',
                      'ALECE_DB_HOST: db'):
            self.assertIn(field, text)
        self.assertNotIn('  app:\n', text)
