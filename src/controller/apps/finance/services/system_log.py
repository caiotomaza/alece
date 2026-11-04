# SPDX-License-Identifier: GPL-3.0-only
"""Append-only audit events with a deliberately small, non-sensitive payload."""
import ipaddress
import re

from apps.core.models import SystemLog

SAFE_DETAILS = frozenset({
    "kind", "role", "method", "status", "original_kind", "original_batch_id",
    "revoked_sessions", "row_number", "batch_id", "rule_id", "profile_id",
})
SAFE_VALUE = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
SAFE_CODE = re.compile(r"[a-z][a-z0-9_]{0,39}\Z")


def _code(value, fallback):
    return value if isinstance(value, str) and SAFE_CODE.fullmatch(value) else fallback


def _details(values):
    result = {}
    for key, value in (values or {}).items():
        if key not in SAFE_DETAILS:
            continue
        if isinstance(value, (bool, int)):
            result[key] = value
        elif isinstance(value, str) and SAFE_VALUE.fullmatch(value):
            result[key] = value
    return result


def _peer_ip(request):
    if request is None:
        return None
    try:
        return str(ipaddress.ip_address(request.META.get("REMOTE_ADDR", "")))
    except ValueError:
        return None


def log_system_event(
    *, module, action, result, description, severity="info", workspace=None,
    profile=None, user=None, request=None, object_type="", object_id="",
    object_repr="", details=None, is_financial_audit=False, ledger_batch_id="",
):
    """Persist identifiers and safe enums; never copy free text or financial values."""
    safe_module = _code(module, "system")
    safe_action = _code(action, "error")
    safe_result = _code(result, "failure")
    safe_severity = _code(severity, "info")
    safe_object_type = object_type if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,49}", object_type) else ""
    safe_object_id = str(object_id) if str(object_id).isdigit() else ""
    safe_ledger_id = str(ledger_batch_id) if str(ledger_batch_id).isdigit() else ""
    return SystemLog.objects.create(
        module=safe_module,
        action=safe_action,
        result=safe_result,
        severity=safe_severity,
        description=f"{safe_module}/{safe_action}",
        details=_details(details),
        workspace=workspace,
        profile=profile,
        user=user,
        ip_address=_peer_ip(request),
        object_type=safe_object_type,
        object_id=safe_object_id,
        object_repr="",
        is_financial_audit=is_financial_audit,
        ledger_batch_id=safe_ledger_id,
    )


def log_financial_event(
    *, action, result, description, workspace, profile, user=None, request=None,
    object_type="", object_id="", object_repr="", details=None,
    ledger_batch_id="", result_status="success", severity="info",
):
    if action in {"login", "logout", "login_failed"}:
        module = "auth"
    elif object_type == "User":
        module = "users"
    elif action in {"reversal", "reverse_item_payments"}:
        module = "reversals"
    elif action in {"transfer"}:
        module = "transfers"
    elif action in {"confirm_outflow"}:
        module = "payments"
    elif "import" in action:
        module = "imports"
    else:
        module = "finance"
    return log_system_event(
        module=module, action=action, result=result, description=description,
        severity=severity, workspace=workspace, profile=profile, user=user,
        request=request, object_type=object_type, object_id=object_id,
        object_repr=object_repr, details=details,
        is_financial_audit=bool(profile and ledger_batch_id),
        ledger_batch_id=ledger_batch_id,
    )


def log_financial_operation(**kwargs):
    """Compatibility entrypoint for existing transactional services."""
    return log_financial_event(**kwargs)


def log_user_action(
    *, action, result, description, workspace, user, request=None, profile=None,
    object_type="", object_id="", object_repr="", details=None,
    result_status="success", severity="info",
):
    return log_system_event(
        module="users", action=action, result=result, description=description,
        severity=severity, workspace=workspace, profile=profile, user=user,
        request=request, object_type=object_type, object_id=object_id,
        object_repr=object_repr, details=details,
    )


def log_error_event(
    *, module, action, description, workspace=None, profile=None, user=None,
    request=None, error_message="", exception=None, details=None, severity="error",
):
    """Never persist exception text, attempted credentials, or user supplied details."""
    return log_system_event(
        module=module, action="error", result="failure", description=description,
        severity=severity, workspace=workspace, profile=profile, user=user,
        request=request, details={"kind": _code(action, "error")},
    )
