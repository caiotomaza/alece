# SPDX-License-Identifier: GPL-3.0-only
"""Management command to verify core dependencies at container startup."""
from django.core.management.base import BaseCommand, CommandError
from apps.core.services.startup import StartupValidator


class Command(BaseCommand):
    help = 'Valida rotas, templates, estáticos, banco e volumes sem alterar dados.'

    def handle(self, *args, **options):
        validator = StartupValidator()
        try:
            for result in validator.run():
                self.stdout.write(f'ALECE STARTUP [{result.name}]: {result.detail}')
        except Exception as exc:
            # Never expose DB credentials, queries or raw exception strings.
            raise CommandError(f'Falha na verificação de inicialização: {type(exc).__name__}') from None
        self.stdout.write(self.style.SUCCESS('ALECE STARTUP: validações críticas concluídas'))
