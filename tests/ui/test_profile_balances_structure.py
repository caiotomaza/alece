# SPDX-License-Identifier: GPL-3.0-only
"""Contrato estático de apresentação da página de saldos, sem conexão a banco."""
from pathlib import Path
import unittest

BASE = Path(__file__).resolve().parents[2]


class ProfileBalancesStructureTests(unittest.TestCase):
    def test_balances_page_uses_shared_tokens_and_semantic_table(self):
        template = (BASE / "src/view/templates/finance/profile_detail.html").read_text()
        css = (BASE / "src/view/static/finance/alece_profile_balances.css").read_text()
        self.assertIn("alece_profile_balances.css", template)
        self.assertIn('aria-labelledby="balances-list-title"', template)
        self.assertIn('scope="col"', template)
        self.assertIn("{% if can_accounts_view %}", template)
        self.assertIn("{% if can_accounts_edit %}", template)
        self.assertIn("account.balance is None", template)
        self.assertIn('class="balances-amount money"', template)
        self.assertIn("{% url 'finance:account-edit'", template)
        self.assertIn("{% url 'finance:choose-profile-action'", template)
        self.assertIn("@media(max-width:700px)", css)
        self.assertIn("@media(max-width:480px)", css)
        self.assertIn("var(--ds-color-surface)", css)
        self.assertNotIn("linear-gradient(", css)


if __name__ == "__main__":
    unittest.main()
