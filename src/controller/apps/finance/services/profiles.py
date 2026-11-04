# SPDX-License-Identifier: GPL-3.0-only
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.finance.models import FinancialProfile, ProfileGrant, Workspace
from apps.finance.services.system_log import log_financial_operation


@transaction.atomic
def create_financial_profile(
    *, workspace_id: int, name: str, emoji: str = "", monthly_income=None, created_by=None,
):
    if created_by is not None:
        from apps.core.permissions import require_workspace_admin
        require_workspace_admin(created_by, workspace_id)
    # Lock the parent to avoid concurrent requests exceeding five profiles.
    workspace = Workspace.objects.select_for_update().get(pk=workspace_id)
    if _active_profiles(workspace.pk).count() >= 5:
        raise ValidationError("Máximo de cinco perfis financeiros por núcleo.")
    profile = FinancialProfile(
        workspace=workspace, name=name.strip(), emoji=emoji, monthly_income=monthly_income,
    )
    profile.full_clean()
    profile.save()
    if created_by is not None:
        ProfileGrant.objects.create(
            membership=workspace.memberships.get(user=created_by),
            profile=profile, can_view=True, can_edit=True,
        )

    # Log do evento de perfil
    log_financial_operation(
        action="create",
        result="success",
        description=f"Perfil financeiro criado: '{profile.name}'",
        workspace=workspace,
        profile=profile,
        user=created_by,
        object_type="FinancialProfile",
        object_id=str(profile.pk),
        object_repr=str(profile),
        details={
            "monthly_income": str(monthly_income) if monthly_income else None,
            "emoji": emoji,
        },
        ledger_batch_id="",
        result_status="success",
        severity="info",
    )

    return profile


def _active_profiles(workspace_id):
    """Ativos são perfis não arquivados e não excluídos (não conta histórico)."""
    return FinancialProfile.objects.filter(
        workspace_id=workspace_id, is_archived=False, deleted_at__isnull=True,
    )


def _require_another_active_profile(profile):
    """Protege o último perfil operacional em todas as operações destrutivas.

    Chamado dentro de transaction.atomic() após bloquear a linha Workspace;
    operações concorrentes de criação, arquivamento e exclusão respeitam esse lock.
    """
    if _active_profiles(profile.workspace_id).exclude(pk=profile.pk).count() < 1:
        raise ValidationError(
            "O espaço financeiro precisa manter ao menos um perfil ativo. "
            "Crie ou reative outro perfil antes de arquivar ou excluir este. "
            "Você ainda pode editar nome, emoji e renda normalmente."
        )


@transaction.atomic
def update_financial_profile(user, profile_id, data):
    from apps.core.permissions import require_profile_view, require_workspace_admin
    profile = require_profile_view(user, profile_id)
    require_workspace_admin(user, profile.workspace_id)
    Workspace.objects.select_for_update().get(pk=profile.workspace_id)
    profile = FinancialProfile.objects.select_for_update().get(pk=profile_id, deleted_at__isnull=True)
    if "is_archived" in data:
        if not profile.is_archived and data["is_archived"]:
            _require_another_active_profile(profile)
        if profile.is_archived and not data["is_archived"]:
            if _active_profiles(profile.workspace_id).count() >= 5:
                raise ValidationError("Máximo de cinco perfis ativos por núcleo.")
    allowed = {"name", "emoji", "monthly_income", "is_archived"}
    if set(data) - allowed:
        raise ValidationError("Campo de perfil não permitido.")

    changes = {}
    for key, value in data.items():
        old_value = getattr(profile, key, None)
        if old_value != value:
            changes[key] = {"old": str(old_value), "new": str(value)}
        setattr(profile, key, value.strip() if isinstance(value, str) else value)
    profile.full_clean()
    profile.save()

    # Log do evento de perfil
    if changes:
        log_financial_operation(
            action="update",
            result="success",
            description=f"Perfil financeiro atualizado: '{profile.name}'",
            workspace=profile.workspace,
            profile=profile,
            user=user,
            object_type="FinancialProfile",
            object_id=str(profile.pk),
            object_repr=str(profile),
            details={"changes": changes},
            ledger_batch_id="",
            result_status="success",
            severity="info",
        )

    return profile


@transaction.atomic
def delete_financial_profile(actor, profile_id, confirmation):
    """Exclusão lógica definitiva sem apagar operações, referências ou auditorias.

    Não executa .delete(): a base financeira referencia o perfil via PROTECT.
    """
    from django.utils import timezone
    from apps.core.permissions import require_workspace_admin

    original = FinancialProfile.objects.get(pk=profile_id)
    require_workspace_admin(actor, original.workspace_id)
    Workspace.objects.select_for_update().get(pk=original.workspace_id)
    profile = FinancialProfile.objects.select_for_update().get(pk=profile_id)
    if profile.deleted_at is not None:
        raise ValidationError("Este perfil já foi excluído.")
    # A palavra de confirmação é verificada no servidor, não apenas no navegador.
    if confirmation != "CONFIRMAR":
        raise ValidationError("Digite CONFIRMAR, em letras maiúsculas, para excluir o perfil.")
    # A identidade 'Principal' não é protegida; a última opção utilizável, sim.
    _require_another_active_profile(profile)

    previous_name = profile.name
    # Nome reservado independente para evitar colisão com perfis existentes.
    from uuid import uuid4
    profile.name = f"Perfil excluído {profile.pk}-{uuid4().hex[:8]}"
    profile.emoji = ""
    profile.is_archived = True
    profile.deleted_at = timezone.now()
    profile.full_clean()
    profile.save(update_fields=["name", "emoji", "is_archived", "deleted_at"])

    # O vínculo de permissão histórica é preservado, mas as concessões são revogadas.
    ProfileGrant.objects.filter(profile=profile).update(
        can_view=False, can_edit=False,
        overview_level=ProfileGrant.Level.NONE,
        accounts_level=ProfileGrant.Level.NONE,
        expenses_level=ProfileGrant.Level.NONE,
        investments_level=ProfileGrant.Level.NONE,
        movements_level=ProfileGrant.Level.NONE,
    )
    log_financial_operation(
        action="delete", result="success", result_status="success", severity="warning",
        description=f"Perfil financeiro excluído logicamente (ID {profile.pk})",
        workspace=profile.workspace, profile=profile, user=actor,
        object_type="FinancialProfile", object_id=str(profile.pk), object_repr=str(profile),
        details={"operation": "soft_delete", "previous_name": previous_name,
                 "financial_records_preserved": True}, ledger_batch_id="",
    )
    return profile
