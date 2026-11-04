# SPDX-License-Identifier: GPL-3.0-only
"""Management command to generate a one-time bootstrap token for initial admin setup."""
import secrets
import hashlib
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import BootstrapToken


class Command(BaseCommand):
    help = "Gera um token único para a configuração inicial do primeiro Administrador."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ttl-hours",
            type=int,
            default=24,
            help="Tempo de vida do token em horas (padrão: 24h).",
        )

    def handle(self, *args, **options):
        # Verificar se já existe algum usuário no sistema
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if User.objects.exists():
            self.stderr.write(self.style.ERROR(
                "Já existem usuários no sistema. O bootstrap inicial não pode ser executado."
            ))
            return

        ttl_hours = options["ttl_hours"]
        
        # Invalidar tokens anteriores
        BootstrapToken.objects.filter(is_used=False).delete()
        
        # Gerar token seguro
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        
        expires_at = timezone.now() + timezone.timedelta(hours=ttl_hours)
        
        BootstrapToken.objects.create(
            token_hash=token_hash,
            expires_at=expires_at,
        )
        
        self.stdout.write(self.style.SUCCESS("Token de bootstrap gerado com sucesso!"))
        self.stdout.write(f"Token: {raw_token}")
        self.stdout.write(f"Expira em: {expires_at.strftime('%d/%m/%Y %H:%M:%S')}")
        self.stdout.write(self.style.WARNING(
            "IMPORTANTE: Guarde este token em local seguro. Ele será exibido apenas uma vez."
        ))
        self.stdout.write("Use este token na tela de configuração inicial em /configuracao-inicial/")