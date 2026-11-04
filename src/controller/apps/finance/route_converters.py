# SPDX-License-Identifier: GPL-3.0-only
"""Human-readable PT-BR path values with stable internal English enums."""
class _TranslatedConverter:
    regex = "[a-z0-9-]+"
    aliases = {}

    def to_python(self, value):
        inverse = {v: k for k, v in self.aliases.items()}
        return inverse.get(value, value)

    def to_url(self, value):
        return self.aliases.get(value, value)


class KindConverter(_TranslatedConverter):
    aliases = {"account": "conta", "recurring": "recorrentes", "unexpected": "imprevistas", "investment": "investimento"}


class ReportConverter(_TranslatedConverter):
    aliases = {"equity": "patrimonio", "investments": "investimentos", "goals": "metas", "dre": "dre"}
