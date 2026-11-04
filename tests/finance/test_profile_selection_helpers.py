# SPDX-License-Identifier: GPL-3.0-only
"""Teste sem Django: a preferência nunca se aplica a outro usuário/núcleo."""
import unittest
from types import SimpleNamespace
from apps.finance.profile_selection import SESSION_KEY, remember_profile, selected_profile_id


class SelectionSessionTests(unittest.TestCase):
    def setUp(self):
        self.request = SimpleNamespace(user=SimpleNamespace(pk=9), session={})

    def test_selection_is_remembered_for_user_workspace(self):
        remember_profile(self.request, 12, 30)
        self.assertEqual(selected_profile_id(self.request, 12), 30)
        self.assertIsNone(selected_profile_id(self.request, 13))
        self.request.user.pk = 77
        self.assertIsNone(selected_profile_id(self.request, 12))

    def test_all_clears_preference(self):
        remember_profile(self.request, 12, 30)
        remember_profile(self.request, 12, None)
        self.assertNotIn(SESSION_KEY, self.request.session)
        self.assertIsNone(selected_profile_id(self.request, 12))

    def test_corrupt_payload_does_not_select_profile(self):
        self.request.session[SESSION_KEY] = {'user_id': 9, 'workspace_id': 12, 'profile_id': '30'}
        self.assertIsNone(selected_profile_id(self.request, 12))
        self.request.session[SESSION_KEY] = {'user_id': 9, 'workspace_id': 12, 'profile_id': True}
        self.assertIsNone(selected_profile_id(self.request, 12))
