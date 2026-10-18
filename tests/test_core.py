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

    def test_landing_requires_login(self):
        """Home page should redirect to login when not authenticated."""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_landing_shows_workspaces_when_logged_in(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.force_login(user)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Meus núcleos')
