# SPDX-License-Identifier: GPL-3.0-only
from django.test import TestCase
from django.urls import reverse


class HealthViewsTests(TestCase):
    def test_liveness(self):
        response = self.client.get(reverse('health-live'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'alive')

    def test_readiness(self):
        response = self.client.get(reverse('health-ready'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ready')

    def test_landing_is_not_a_fake_production_dashboard(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Base de desenvolvimento')
