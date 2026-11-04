# SPDX-License-Identifier: GPL-3.0-only
from django.test import SimpleTestCase
from django.urls import reverse, resolve


class WebRoutesTests(SimpleTestCase):
    def test_all_public_pages_have_stable_ptbr_routes(self):
        for name, route in {
            'visao-geral':'/visao-geral/', 'despesas':'/despesas/',
            'investimentos':'/investimentos/', 'movimentacoes':'/movimentacoes/',
            'configuracoes':'/configuracoes/', 'logs':'/logs/',
            'relatorios':'/relatorios/',
        }.items():
            with self.subTest(name=name):
                self.assertEqual(reverse(name), route)
                self.assertEqual(resolve(route).url_name, name)
