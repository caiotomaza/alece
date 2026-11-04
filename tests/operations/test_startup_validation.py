# SPDX-License-Identifier: GPL-3.0-only
from unittest.mock import patch
from django.test import SimpleTestCase
from apps.core.services.startup import CheckResult, StartupValidator


class StartupValidationTests(SimpleTestCase):
    def test_checks_executed_in_defined_order(self):
        validator = StartupValidator()
        with patch.object(validator, 'routes'), patch.object(validator, 'templates'), \
             patch.object(validator, 'statics'), patch.object(validator, 'database'), \
             patch.object(validator, 'schema'), patch.object(validator, 'storage'):
            results = validator.run()
        self.assertEqual([r.name for r in results],
                         ['rotas', 'templates', 'estaticos', 'banco', 'schema', 'volumes'])
        self.assertTrue(all(r.detail == 'OK' for r in results))

    def test_failure_halts_validation(self):
        validator = StartupValidator()
        with patch.object(validator, 'routes', side_effect=RuntimeError('bad')):
            with self.assertRaises(RuntimeError):
                validator.run()
        self.assertEqual(validator.results, [])

    def test_url_reverse_resolve_for_all_public_pages(self):
        StartupValidator().routes()

    def test_required_templates_resolve(self):
        StartupValidator().templates()

    def test_required_static_assets_exist(self):
        StartupValidator().statics()
