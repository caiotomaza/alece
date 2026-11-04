# SPDX-License-Identifier: GPL-3.0-only
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.finance.models import FinancialProfile, Workspace
from apps.finance.services.profiles import create_financial_profile


class FinancialProfileLimitsTests(TestCase):
    def test_up_to_five_profiles_per_workspace_in_service(self):
        user = get_user_model().objects.create_user(username='owner', password='test-secret')
        workspace = Workspace.objects.create(name='Casa', created_by=user)
        for index in range(5):
            create_financial_profile(workspace_id=workspace.pk, name=f'Perfil {index}')
        self.assertEqual(FinancialProfile.objects.filter(workspace=workspace).count(), 5)
        with self.assertRaises(ValidationError):
            create_financial_profile(workspace_id=workspace.pk, name='Perfil 6')
