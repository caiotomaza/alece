# SPDX-License-Identifier: GPL-3.0-only
"""Modelos de usuário estendidos para recuperação offline e preferências."""
from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    """Perfil estendido do usuário para campos não presentes no User padrão."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    # Hash do código de recuperação offline (SHA-256)
    recovery_code_hash = models.CharField(max_length=64, blank=True, null=True)
    # Version zero codes may have been issued by the insecure legacy endpoint.
    recovery_code_version = models.PositiveSmallIntegerField(default=0)
    # Timestamp de criação do código de recuperação
    recovery_code_created = models.DateTimeField(blank=True, null=True)
    # Preferência de tema (light/dark/auto)
    theme = models.CharField(max_length=10, default="auto", choices=[
        ("light", "Claro"),
        ("dark", "Escuro"),
        ("auto", "Sistema"),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil do usuário"
        verbose_name_plural = "Perfis dos usuários"

    def __str__(self):
        return f"Perfil de {self.user.username}"

    def has_recovery_code(self) -> bool:
        """Verifica se há código de recuperação ativo."""
        return bool(self.recovery_code_hash) and self.recovery_code_version == 1

    def verify_recovery_code(self, code: str) -> bool:
        """Verifica se o código de recuperação confere com o hash armazenado."""
        if not self.has_recovery_code():
            return False
        import hashlib
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        from django.utils.crypto import constant_time_compare
        return constant_time_compare(code_hash, self.recovery_code_hash)

    def set_recovery_code(self, code: str) -> None:
        """Define novo código de recuperação (hash)."""
        import hashlib
        from django.utils import timezone
        self.recovery_code_hash = hashlib.sha256(code.encode()).hexdigest()
        self.recovery_code_version = 1
        self.recovery_code_created = timezone.now()
        self.save(update_fields=["recovery_code_hash", "recovery_code_version", "recovery_code_created", "updated_at"])

    def clear_recovery_code(self) -> None:
        """Remove o código de recuperação após uso."""
        self.recovery_code_hash = None
        self.recovery_code_created = None
        self.save(update_fields=["recovery_code_hash", "recovery_code_created", "updated_at"])


class AuthenticationAttempt(models.Model):
    """Shared rate-limit bucket; identifiers and credentials are never stored."""

    key = models.CharField(max_length=64, unique=True)
    window_started = models.DateTimeField(db_index=True)
    attempts = models.PositiveIntegerField(default=0)
