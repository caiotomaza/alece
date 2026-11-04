# SPDX-License-Identifier: GPL-3.0-only
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

from django.test import SimpleTestCase
from django.urls import resolve, reverse
from apps.core.ai_catalog import PROVIDERS, SECTIONS
from apps.core.settings_forms import AIProviderConfigForm
from apps.finance.route_converters import KindConverter, ReportConverter


class AiPresetTests(SimpleTestCase):
    def test_preset_requires_key(self):
        for code in PROVIDERS:
            self.assertFalse(AIProviderConfigForm({"provider_type": code}).is_valid())
            self.assertTrue(AIProviderConfigForm({"provider_type": code, "api_token": "sample-token"}).is_valid())

    def test_no_endpoint_or_sections_from_client(self):
        form = AIProviderConfigForm({"provider_type": "openai", "api_token": "sample-token", "endpoint": "https://localhost", "sections": ["expenses"]})
        self.assertTrue(form.is_valid())
        # Campos manipulados no POST são substituídos pelos valores pinados no catálogo.
        self.assertEqual(form.cleaned_data["endpoint"], PROVIDERS["openai"]["endpoint"])
        self.assertEqual(form.cleaned_data["model_name"], PROVIDERS["openai"]["model"])
        self.assertNotIn("sections", form.cleaned_data)
        self.assertEqual(len(SECTIONS), 3)

    def test_canonical_routes(self):
        self.assertEqual(reverse("finance:profile-manage", args=[7]), "/financas/perfis/7/gerenciar/")
        self.assertEqual(reverse("finance:import-upload", args=[7]), "/financas/perfis/7/importacoes/novo/")
        self.assertEqual(reverse("login"), "/entrar/")
        self.assertEqual(reverse("password_change"), "/senha/alterar/")
        self.assertEqual(reverse("core:user-edit", args=[4, 9]), "/sistema/usuarios/4/9/editar/")

    def test_legacy_resolves(self):
        self.assertIsNotNone(resolve("/finance/profiles/7/edit/"))
        self.assertIsNotNone(resolve("/login/"))
        self.assertIsNotNone(resolve("/core/users/4/9/edit/"))

    def test_kind_round_trip(self):
        converter = KindConverter()
        self.assertEqual(converter.to_python(converter.to_url("recurring")), "recurring")
        self.assertEqual(ReportConverter().to_url("equity"), "patrimonio")


class TokenFileTests(TestCase):
    def test_store_and_read_with_strict_mode(self):
        from apps.core import ai_credentials
        with TemporaryDirectory() as directory, mock.patch.object(ai_credentials, "SECRET_DIR", Path(directory)/"secrets"):
            ai_credentials.write_token(1, "  test-secret  ")
            self.assertEqual(ai_credentials.read_token(1), "test-secret")
            self.assertEqual((Path(directory)/"secrets"/"provider-1.key").stat().st_mode & 0o777, 0o600)
            self.assertFalse(ai_credentials.has_token(2))
            with self.assertRaises(ValueError):
                ai_credentials.write_token(1, "bad\nkey")
