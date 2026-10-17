# SPDX-License-Identifier: GPL-3.0-only
"""Sistema de permissões e autorização para isolamento de workspaces e perfis financeiros."""
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

from apps.finance.models import FinancialProfile, ProfileGrant, WorkspaceMembership

User = get_user_model()


class PermissionError(PermissionDenied):
    """Erro de permissão personalizado para o ALECE."""
    pass


def get_user_workspace_memberships(user):
    """Retorna todas as memberships ativas do usuário."""
    return WorkspaceMembership.objects.filter(user=user).select_related("workspace")


def get_user_workspaces(user):
    """Retorna workspaces onde o usuário tem membership."""
    return [m.workspace for m in get_user_workspace_memberships(user)]


def user_has_workspace_access(user, workspace_id) -> bool:
    """Verifica se o usuário tem acesso ao workspace."""
    return WorkspaceMembership.objects.filter(user=user, workspace_id=workspace_id).exists()


def user_has_workspace_role(user, workspace_id, role: str) -> bool:
    """Verifica se o usuário tem o papel especificado no workspace."""
    return WorkspaceMembership.objects.filter(
        user=user, workspace_id=workspace_id, role=role
    ).exists()


def user_is_workspace_admin(user, workspace_id) -> bool:
    """Verifica se o usuário é admin do workspace."""
    return user_has_workspace_role(user, workspace_id, WorkspaceMembership.Role.ADMIN)


def get_user_profile_grants(user, profile_id):
    """Retorna grants do usuário para um perfil financeiro específico."""
    memberships = WorkspaceMembership.objects.filter(user=user).values_list("pk", flat=True)
    return ProfileGrant.objects.filter(
        membership_id__in=memberships, profile_id=profile_id
    ).first()


def user_can_view_profile(user, profile_id) -> bool:
    """Verifica se o usuário pode visualizar o perfil financeiro."""
    grant = get_user_profile_grants(user, profile_id)
    return grant is not None and grant.can_view


def user_can_edit_profile(user, profile_id) -> bool:
    """Verifica se o usuário pode editar o perfil financeiro."""
    grant = get_user_profile_grants(user, profile_id)
    return grant is not None and grant.can_edit


def get_accessible_profiles(user):
    """Retorna queryset de perfis financeiros que o usuário pode visualizar."""
    memberships = WorkspaceMembership.objects.filter(user=user).values_list("pk", flat=True)
    granted_profile_ids = ProfileGrant.objects.filter(
        membership_id__in=memberships, can_view=True
    ).values_list("profile_id", flat=True)
    return FinancialProfile.objects.filter(pk__in=granted_profile_ids)


def get_editable_profiles(user):
    """Retorna queryset de perfis financeiros que o usuário pode editar."""
    memberships = WorkspaceMembership.objects.filter(user=user).values_list("pk", flat=True)
    granted_profile_ids = ProfileGrant.objects.filter(
        membership_id__in=memberships, can_edit=True
    ).values_list("profile_id", flat=True)
    return FinancialProfile.objects.filter(pk__in=granted_profile_ids)


def require_workspace_access(user, workspace_id):
    """Levanta PermissionError se o usuário não tem acesso ao workspace."""
    if not user_has_workspace_access(user, workspace_id):
        raise PermissionError("Acesso negado a este núcleo.")


def require_workspace_admin(user, workspace_id):
    """Levanta PermissionError se o usuário não é admin do workspace."""
    if not user_is_workspace_admin(user, workspace_id):
        raise PermissionError("Apenas administradores do núcleo podem realizar esta ação.")


def require_profile_view(user, profile_id):
    """Levanta PermissionError se o usuário não pode visualizar o perfil. Retorna o perfil se autorizado."""
    try:
        profile = FinancialProfile.objects.get(pk=profile_id)
    except FinancialProfile.DoesNotExist:
        raise PermissionError("Perfil financeiro não encontrado.")
    
    if not user_can_view_profile(user, profile_id):
        raise PermissionError("Acesso negado a este perfil financeiro.")
    
    return profile


def require_profile_edit(user, profile_id):
    """Levanta PermissionError se o usuário não pode editar o perfil."""
    if not user_can_edit_profile(user, profile_id):
        raise PermissionError("Permissão de edição negada para este perfil financeiro.")


def require_profile_ownership(user, profile_id):
    """Verifica se o perfil pertence a um workspace do usuário."""
    try:
        profile = FinancialProfile.objects.get(pk=profile_id)
    except FinancialProfile.DoesNotExist:
        raise PermissionError("Perfil financeiro não encontrado.")
    
    if not user_has_workspace_access(user, profile.workspace_id):
        raise PermissionError("Acesso negado a este perfil financeiro.")
    
    return profile


def filter_queryset_by_user_access(queryset, user, profile_field="profile"):
    """
    Filtra um queryset para incluir apenas objetos de perfis acessíveis ao usuário.
    
    Args:
        queryset: QuerySet base
        user: Usuário atual
        profile_field: Nome do campo que referencia FinancialProfile (padrão: 'profile')
    
    Returns:
        QuerySet filtrado
    """
    accessible_profile_ids = get_accessible_profiles(user).values_list("pk", flat=True)
    filter_kwargs = {f"{profile_field}__in": accessible_profile_ids}
    return queryset.filter(**filter_kwargs)