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
    recovery_acknowledged_at = models.DateTimeField(null=True, blank=True)
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
        return (RecoveryCode.objects.filter(user_id=self.user_id, used_at__isnull=True).exists() or
                (bool(self.recovery_code_hash) and self.recovery_code_version == 1))

    def verify_recovery_code(self, code: str) -> bool:
        """Verifica se o código de recuperação confere com o hash armazenado."""
        # Verifica somente o formato legado (hash unitario), nunca os seis codigos v2.
        if self.recovery_code_version != 1 or not self.recovery_code_hash:
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


class RecoveryCode(models.Model):
    """Recovery codes are individually consumed; never store plaintext."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="recovery_codes")
    slot = models.PositiveSmallIntegerField()
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=("user", "slot"), name="uq_recovery_slot_user")]



class AuthenticationAttempt(models.Model):
    """Shared rate-limit bucket; identifiers and credentials are never stored."""

    key = models.CharField(max_length=64, unique=True)
    window_started = models.DateTimeField(db_index=True)
    attempts = models.PositiveIntegerField(default=0)


class BootstrapToken(models.Model):
    """Token de uso único para configuração inicial do primeiro Administrador.
    
    Gerado via console administrativo (manage.py generate_bootstrap_token),
    permite a criação do primeiro Administrador em /setup/.
    """
    token_hash = models.CharField(max_length=64, unique=True)
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(blank=True, null=True)
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="bootstrap_tokens_used",
    )
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Token de bootstrap"
        verbose_name_plural = "Tokens de bootstrap"

    def __str__(self):
        return f"BootstrapToken {'(usado)' if self.is_used else '(válido)'} até {self.expires_at}"

    def is_valid(self) -> bool:
        from django.utils import timezone
        return not self.is_used and self.expires_at > timezone.now()

    def mark_used(self, user):
        from django.utils import timezone
        self.is_used = True
        self.used_at = timezone.now()
        self.used_by = user
        self.save(update_fields=["is_used", "used_at", "used_by"])

    @classmethod
    def validate_token(cls, raw_token: str):
        import hashlib
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        try:
            token = cls.objects.get(token_hash=token_hash)
            if token.is_valid():
                return token
        except cls.DoesNotExist:
            pass
        return None


class SystemLog(models.Model):
    """Log de auditoria do sistema para eventos administrativos e operacionais.
    
    Registra eventos de autenticação, gestão de usuários, permissões,
    perfis financeiros, contas, transações, importações, erros, etc.
    Diferencia logs técnicos de eventos de auditoria financeira.
    """
    
    class Severity(models.TextChoices):
        DEBUG = "debug", "Debug"
        INFO = "info", "Info"
        WARNING = "warning", "Aviso"
        ERROR = "error", "Erro"
        CRITICAL = "critical", "Crítico"
    
    class Module(models.TextChoices):
        AUTH = "auth", "Autenticação"
        USERS = "users", "Usuários"
        PERMISSIONS = "permissions", "Permissões"
        PROFILES = "profiles", "Perfis Financeiros"
        ACCOUNTS = "accounts", "Contas"
        EXPENSES = "expenses", "Despesas"
        INVESTMENTS = "investments", "Investimentos"
        MOVEMENTS = "movements", "Movimentações"
        PAYMENTS = "payments", "Pagamentos"
        TRANSFERS = "transfers", "Transferências"
        INVESTMENTS_OPS = "investments_ops", "Aplicações/Resgates"
        REVERSALS = "reversals", "Estornos"
        IMPORTS = "imports", "Importações"
        RECONCILIATION = "reconciliation", "Conciliações"
        SETTINGS = "settings", "Configurações"
        BOOTSTRAP = "bootstrap", "Primeiro Acesso"
        SYSTEM = "system", "Sistema"
        ADMIN = "admin", "Administração"
    
    class Action(models.TextChoices):
        LOGIN = "login", "Login"
        LOGOUT = "logout", "Logout"
        LOGIN_FAILED = "login_failed", "Falha no Login"
        CREATE = "create", "Criação"
        UPDATE = "update", "Atualização"
        DELETE = "delete", "Exclusão"
        ARCHIVE = "archive", "Arquivamento"
        VIEW = "view", "Visualização"
        PERMISSION_GRANT = "permission_grant", "Concessão de Permissão"
        PERMISSION_REVOKE = "permission_revoke", "Revogação de Permissão"
        PAYMENT = "payment", "Pagamento"
        TRANSFER = "transfer", "Transferência"
        APPLICATION = "application", "Aplicação"
        REDEMPTION = "redemption", "Resgate"
        REVERSAL = "reversal", "Estorno"
        IMPORT = "import", "Importação"
        RECONCILE = "reconcile", "Conciliação"
        SETUP = "setup", "Configuração Inicial"
        TOKEN_GENERATED = "token_generated", "Token Gerado"
        TOKEN_USED = "token_used", "Token Utilizado"
        TOKEN_REUSED = "token_reused", "Tentativa de Reuso de Token"
        ERROR = "error", "Erro"
        SETTING_CHANGE = "setting_change", "Alteração de Configuração"
    
    class Result(models.TextChoices):
        SUCCESS = "success", "Sucesso"
        FAILURE = "failure", "Falha"
        DENIED = "denied", "Negado"
        PARTIAL = "partial", "Parcial"
    
    # Identificação
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.INFO)
    module = models.CharField(max_length=20, choices=Module.choices)
    action = models.CharField(max_length=30, choices=Action.choices)
    result = models.CharField(max_length=10, choices=Result.choices, default=Result.SUCCESS)
    
    # Detalhes
    description = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    
    # Contexto
    workspace = models.ForeignKey(
        "finance.Workspace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="system_logs",
        help_text="Núcleo financeiro relacionado (se aplicável)"
    )
    profile = models.ForeignKey(
        "finance.FinancialProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="system_logs",
        help_text="Perfil financeiro relacionado (se aplicável)"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="system_logs",
        help_text="Usuário responsável pela ação"
    )
    request_id = models.CharField(max_length=64, blank=True, help_text="Identificador único da requisição")
    ip_address = models.GenericIPAddressField(null=True, blank=True, help_text="Endereço IP de origem")
    user_agent = models.TextField(blank=True, help_text="User-Agent do cliente")
    
    # Referência ao objeto afetado
    object_type = models.CharField(max_length=50, blank=True, help_text="Tipo do objeto afetado (ex: Transaction, InvestmentPosition)")
    object_id = models.CharField(max_length=64, blank=True, help_text="ID do objeto afetado")
    object_repr = models.CharField(max_length=255, blank=True, help_text="Representação textual do objeto")
    
    # Auditoria financeira
    is_financial_audit = models.BooleanField(default=False, help_text="Se True, evento de auditoria financeira (linked to ledger)")
    ledger_batch_id = models.CharField(max_length=64, blank=True, help_text="ID do lote contábil relacionado (se aplicável)")
    
    class Meta:
        verbose_name = "Log do Sistema"
        verbose_name_plural = "Logs do Sistema"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["-timestamp"]),
            models.Index(fields=["workspace", "-timestamp"]),
            models.Index(fields=["user", "-timestamp"]),
            models.Index(fields=["module", "-timestamp"]),
            models.Index(fields=["severity", "-timestamp"]),
            models.Index(fields=["is_financial_audit", "-timestamp"]),
        ]
    
    def __str__(self):
        return f"[{self.timestamp:%Y-%m-%d %H:%M:%S}] {self.module}/{self.action} - {self.result} - {self.user or 'Sistema'}"


class SystemLogManager(models.Manager):
    """Manager customizado para SystemLog com métodos de conveniência."""
    
    def log_event(self, *, module, action, result, description, severity="info",
                  workspace=None, profile=None, user=None, request=None,
                  object_type="", object_id="", object_repr="",
                  details=None, is_financial_audit=False, ledger_batch_id=""):
        """Cria um novo registro de log."""
        details_dict = details or {}
        
        # Extrair info da request se disponível
        request_id = ""
        ip_address = None
        user_agent = ""
        if request:
            # Identificadores fornecidos pelo cliente não são evidência confiável de auditoria.
            request_id = ""
            ip_address = self._get_client_ip(request)
            user_agent = ""
        
        return self.create(
            severity=severity,
            module=module,
            action=action,
            result=result,
            description=description,
            details=details_dict,
            workspace=workspace,
            profile=profile,
            user=user,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            object_type=object_type,
            object_id=str(object_id) if object_id else "",
            object_repr=object_repr,
            is_financial_audit=is_financial_audit,
            ledger_batch_id=ledger_batch_id,
        )
    
    def _get_client_ip(self, request):
        """Extrai IP do cliente considerando proxies."""
        # Usar somente IP do par. X-Forwarded-For pode ser falsificado pelo cliente.
        import ipaddress
        try:
            return str(ipaddress.ip_address(request.META.get("REMOTE_ADDR", "")))
        except ValueError:
            return None


class AIProviderConfig(models.Model):
    """Integration metadata only. Credentials remain out of PostgreSQL."""
    class Section(models.TextChoices):
        EXPENSES = "expenses", "Despesas"
        INVESTMENTS = "investments", "Investimentos"
        MOVEMENTS = "movements", "Movimentações"

    workspace = models.ForeignKey("finance.Workspace", on_delete=models.CASCADE, related_name="ai_providers")
    name = models.CharField(max_length=100)
    endpoint = models.URLField(max_length=500)
    model_name = models.CharField(max_length=120)
    api_key_env = models.CharField(max_length=80, blank=True)
    sections = models.JSONField(default=list)
    enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name", "pk")
        constraints = [
            models.UniqueConstraint(fields=("workspace", "name"), name="uq_alece_ai_provider_name"),
            models.UniqueConstraint(fields=("workspace",), condition=models.Q(enabled=True), name="uq_alece_ai_one_active_ws"),
        ]


class AIAnalysis(models.Model):
    """Stored advisory output, never an automatic change to the financial ledger."""
    workspace = models.ForeignKey("finance.Workspace", on_delete=models.CASCADE)
    profile = models.ForeignKey("finance.FinancialProfile", on_delete=models.CASCADE)
    provider = models.ForeignKey(AIProviderConfig, on_delete=models.PROTECT)
    section = models.CharField(max_length=12, choices=AIProviderConfig.Section.choices)
    summary = models.TextField(max_length=4000)
    data_hash = models.CharField(max_length=64)
    record_count = models.PositiveSmallIntegerField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("profile", "section", "-created_at"), name="alece_ai_analysis_idx")]
