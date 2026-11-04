"""Guards for the standalone, synthetic Docker validation stack (no Docker required)."""
import json
import os
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
MODULE = runpy.run_path(str(ROOT / 'scripts' / 'Validar-ALECE-Isolado.py'),
                        run_name='alece_validation_tests')


class IsolatedValidationStackTests(unittest.TestCase):
    def setUp(self):
        self.project = 'alece_val_isolado_abcdefghij'
        self.good = {
            'name': self.project,
            'networks': {'validation': {'internal': True}},
            'volumes': {'app_pgdata': {'name': self.project + '_app_pgdata'}},
            'services': {
                'web': {'environment': {'ALECE_VALIDATION_ONLY': '1',
                                        'ALECE_DB_NAME': 'alece_audit',
                                        'ALECE_DB_USER': 'alece_audit',
                                        'ALECE_DB_HOST': 'db'},
                        'volumes': [{'type': 'volume', 'source': 'app_pgdata'}]},
                'db': {'volumes': [{'type': 'volume', 'source': 'app_pgdata'}]},
            },
        }

    def test_expected_isolated_compose_is_accepted(self):
        self.assertTrue(MODULE['assert_config_isolated'](json.dumps(self.good)))

    def test_rejects_fixed_container_names_even_with_project_flag(self):
        self.good['services']['web']['container_name'] = 'alece_web'
        with self.assertRaises(MODULE['ValidationError']):
            MODULE['assert_config_isolated'](json.dumps(self.good))

    def test_rejects_host_ports(self):
        self.good['services']['web']['ports'] = [{'published': '8088'}]
        with self.assertRaises(MODULE['ValidationError']):
            MODULE['assert_config_isolated'](json.dumps(self.good))

    def test_rejects_external_or_wrongly_named_volumes(self):
        for volume in ({'name': 'alece_app_pgdata'}, {'external': True,
                       'name': self.project + '_app_pgdata'}):
            with self.subTest(volume=volume):
                self.good['volumes']['app_pgdata'] = volume
                with self.assertRaises(MODULE['ValidationError']):
                    MODULE['assert_config_isolated'](json.dumps(self.good))

    def test_rejects_host_bind_mounts(self):
        self.good['services']['db']['volumes'] = [{'type': 'bind', 'source': '/home/user/data'}]
        with self.assertRaises(MODULE['ValidationError']):
            MODULE['assert_config_isolated'](json.dumps(self.good))

    def test_rejects_external_network(self):
        self.good['networks']['validation']['internal'] = False
        with self.assertRaises(MODULE['ValidationError']):
            MODULE['assert_config_isolated'](json.dumps(self.good))

    def test_inherited_alece_configuration_is_discarded(self):
        with patch.dict(os.environ, {'ALECE_DB_HOST': 'example.internal',
                                  'ALECE_DB_PASSWORD': 'private',
                                  'COMPOSE_PROJECT_NAME': 'alece',
                                  'PATH': '/bin'}, clear=True):
            clean = MODULE['safe_environment']()
        self.assertEqual(clean, {'PATH': '/bin'})

    def test_validation_compose_does_not_use_production_stack(self):
        text = (ROOT / 'compose.validation.yaml').read_text(encoding='utf-8')
        self.assertNotIn('container_name:', text)
        self.assertNotIn('external: true', text)
        self.assertNotIn('app_pgdata:/var/lib/postgresql/data:', text)
        self.assertIn('internal: true', text)
        self.assertIn('ALECE_VALIDATION_ONLY: "1"', text)
        self.assertIn('POSTGRES_DB: alece_audit', text)
        self.assertNotIn('path: ./.env\n', text)
        self.assertIn('required: true', text)
        self.assertIn('app_pgdata:/var/lib/postgresql/data', text)


if __name__ == '__main__':
    unittest.main()
