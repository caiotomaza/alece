# SPDX-License-Identifier: GPL-3.0-only
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Q
from django.http import JsonResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.conf import settings
from pathlib import Path
import re

from apps.core.models import SystemLog
from apps.core.permissions import get_user_workspace_memberships
from apps.finance.models import WorkspaceMembership

User = get_user_model()


def is_system_initialized():
    """Verifica se o sistema já foi inicializado (existe pelo menos um usuário)."""
    return User.objects.exists()


@require_GET
def index(request):
    if not is_system_initialized():
        return redirect("setup")
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login')}?next=/")
    memberships = get_user_workspace_memberships(request.user).order_by("workspace_id")
    if memberships.count() == 1:
        return redirect("visao-geral")
    # Multiple memberships: keep a real workspace chooser on the home page.
    return render(request, "index.html", {"memberships": memberships})


@require_GET
def live(request):
    return JsonResponse({"status": "alive"})


@require_GET
def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ready"})


@require_GET
def healthz(request):
    """Health check endpoint for container orchestration (ZimaOS, Kubernetes, etc.).
    Returns 200 OK with minimal JSON payload. No authentication required.
    Never exposes balances, settings, or stack traces.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "error"}, status=503)
    return JsonResponse({"status": "ok"})


def about_page(request):
    """Página 'Sobre o projeto' - página interna (não modal).
    Roteiro v1.32.1: ALECE grátis/self-hosted/GPL-3.0-only, homenagem à Alice,
    Lógica da ferramenta com <details>/<summary>, Como usar em 4 etapas,
    SVGs inline das bandeiras Brasil/Ceará/NTEC, links oficiais.
    """
    return render(request, "about.html", {})


def _visible_system_logs(user):
    """Full system logs are available only to current workspace administrators."""
    logs = SystemLog.objects.select_related("user", "workspace", "profile")
    if user.is_superuser and user.is_active:
        return logs
    admin_workspace_ids = WorkspaceMembership.objects.filter(
        user=user, user__is_active=True, role=WorkspaceMembership.Role.ADMIN,
    ).values("workspace_id")
    if not admin_workspace_ids.exists():
        raise PermissionDenied("Logs do Sistema exigem papel Administrador.")
    return logs.filter(workspace_id__in=admin_workspace_ids)


@login_required
@require_GET
def system_logs_list(request):
    """Lista de logs do sistema com filtros e paginação."""
    user = request.user

    logs = _visible_system_logs(user).order_by("-timestamp", "-pk")
    selected_log = None
    open_id = request.GET.get("abrir")
    if open_id is not None:
        if not open_id.isdecimal() or len(open_id) > 18:
            raise Http404("Log invalido")
        selected_log = get_object_or_404(logs, pk=int(open_id))
        # A visao de detalhe deve conter o log mesmo que filtros antigos estejam ativos.
        request_filters_enabled = False
    else:
        request_filters_enabled = True

    # Filtros
    severity = request.GET.get("severity")
    module = request.GET.get("module")
    action = request.GET.get("action")
    result = request.GET.get("result")
    user_filter = request.GET.get("user")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    search = request.GET.get("search")

    if request_filters_enabled and severity:
        logs = logs.filter(severity=severity)
    if request_filters_enabled and module:
        logs = logs.filter(module=module)
    if request_filters_enabled and action:
        logs = logs.filter(action=action)
    if request_filters_enabled and result:
        logs = logs.filter(result=result)
    if request_filters_enabled and user_filter:
        logs = logs.filter(user__username__icontains=user_filter)
    if request_filters_enabled and date_from:
        logs = logs.filter(timestamp__date__gte=date_from)
    if request_filters_enabled and date_to:
        logs = logs.filter(timestamp__date__lte=date_to)
    if request_filters_enabled and search:
        logs = logs.filter(
            Q(description__icontains=search) |
            Q(details__icontains=search) |
            Q(user__username__icontains=search) |
            Q(object_repr__icontains=search)
        )

    # Paginação
    paginator = Paginator(logs, 50)
    page_number = request.GET.get("page", 1)
    if selected_log is not None:
        # Pagina correta para o registro no ordenamento data/PK decrescente.
        newer_count = logs.filter(
            Q(timestamp__gt=selected_log.timestamp) |
            Q(timestamp=selected_log.timestamp, pk__gt=selected_log.pk)
        ).count()
        page_number = newer_count // 50 + 1
    page_obj = paginator.get_page(page_number)

    # Opções para filtros
    severity_choices = SystemLog.Severity.choices
    module_choices = SystemLog.Module.choices
    action_choices = SystemLog.Action.choices
    result_choices = SystemLog.Result.choices
    admin_membership = WorkspaceMembership.objects.filter(
        user=request.user, user__is_active=True,
        role=WorkspaceMembership.Role.ADMIN,
    ).select_related("workspace").order_by("workspace_id").first()

    context = {
        "page_obj": page_obj,
        "selected_log_id": selected_log.pk if selected_log else None,
        "severity_choices": severity_choices,
        "module_choices": module_choices,
        "action_choices": action_choices,
        "result_choices": result_choices,
        "filters": {
            "severity": severity,
            "module": module,
            "action": action,
            "result": result,
            "user": user_filter,
            "date_from": date_from,
            "date_to": date_to,
            "search": search,
        },
        "active_nav": "system-logs",
        "workspace": admin_membership.workspace if admin_membership else None,
        "title": "Logs do Sistema",
    }

    return render(request, "core/system_logs_list.html", context)


@login_required
@require_GET
def system_logs_legacy_redirect(request):
    """Alias antigo, sem introduzir novas rotas publicas de auditoria."""
    target = reverse("logs")
    if request.GET:
        target += "?" + request.GET.urlencode()
    return redirect(target)


@login_required
@require_GET
def system_log_detail(request, log_id):
    """Links antigos apontam para /logs/ com o registro expandido."""
    get_object_or_404(_visible_system_logs(request.user), pk=log_id)
    return redirect(f"{reverse('logs')}?abrir={log_id}#log-{log_id}")


def _safe_diagnostic_line(line):
    """Oculta segredos conhecidos em logs textuais antes de exportar."""
    # Sem refletir credenciais em claro. Evita tentar normalizar trilhas completas.
    # Credenciais em cabecalhos e variaveis de ambiente: ocultar a linha inteira.
    if re.search(r"(?i)\b(authorization|set-cookie|cookie|bearer)\b\s*[:= ]|"
                 r"(?i:ALECE_SECRET_KEY|DATABASE_URL|OPENAI_API_KEY|API[_-]?SECRET)", line):
        return "[REDACTED: credenciais no log]"
    # Treat the entire line as sensitive: JSON quotes, spaces in values and URL
    # query strings make partial substitution unsafe. Keep the original log on
    # the server for incident responders, never in an HTTP diagnostic export.
    if re.search(
        r"(?i)\b(?:password|passwd|secret|token|access_token|refresh_token|"
        r"id_token|api[_-]?token|api[_-]?key|client[_-]?secret|private[_-]?key|"
        r"secret[_-]?key|db[_-]?password|sessionid|session[_-]?key|csrftoken)"
        r"\b[\"']?\s*[:=]", line
    ):
        return "[REDACTED: credenciais no log]"
    return line


def _recent_runtime_logs():
    """Copia um trecho pequeno de no maximo dois logs de inicializacao."""
    folder = Path(settings.BASE_DIR) / "src" / "logs"
    if not folder.is_dir():
        return "Log operacional: pasta inexistente.\n"
    files = sorted((p for p in folder.glob("*.log") if p.is_file() and not p.is_symlink()),
                   key=lambda p: p.name, reverse=True)[:2]
    chunks = []
    for filepath in files:
        try:
            with filepath.open("rb") as f:
                f.seek(0, 2)
                f.seek(max(0, f.tell() - 48_000))
                blob = f.read(48_000)
            # Nunca incluir bytes binarios ou cabecalhos arbitrarios.
            excerpt = blob.decode("utf-8", "replace")
            lines = excerpt.splitlines()[-180:]
            chunks.append(f"--- {filepath.name} (trecho final) ---\n" +
                          "\n".join(_safe_diagnostic_line(line) for line in lines))
        except OSError:
            chunks.append(f"--- {filepath.name}: nao foi possivel ler ---")
    return "\n\n".join(chunks) or "Nao ha logs operacionais registrados."


@login_required
@require_GET
def system_logs_diagnostic(request):
    """Exporta auditoria e logs recentes, exclusivamente para administradores."""
    from django.utils.timezone import now
    logs = list(_visible_system_logs(request.user).order_by("-timestamp", "-pk")[:80])
    rows = [
        "ALECE | Diagnostico recente (somente administrador)",
        f"Capturado em: {now().isoformat()}",
        "Fonte: registros de auditoria autorizados e arquivos operacionais recentes",
        "Nao inclui senhas, tokens ou cookies intencionalmente.",
        "",
        "=== ULTIMOS EVENTOS DE AUDITORIA ===",
    ]
    for entry in logs:
        # Dados do banco incluem historico financeiro e sao restritos por nucleo.
        rows.append(_safe_diagnostic_line(
            f"{entry.timestamp.isoformat()} | ID={entry.pk} | "
            f"{entry.get_severity_display()} | {entry.get_module_display()} | "
            f"{entry.get_action_display()} | {entry.get_result_display()} | "
            f"{entry.description}"))
    # Logs operacionais podem conter eventos de outros nucleos no mesmo servidor.
    # Apenas superusuarios autenticados podem receber esse trecho transversal.
    if request.user.is_active and request.user.is_superuser:
        runtime_section = _recent_runtime_logs()
    else:
        runtime_section = "Restrito a superusuarios do servidor; eventos de auditoria do nucleo acima."
    rows += ["", "=== LOGS DE EXECUCAO DO CONTAINER (ULTIMOS TRECHOS) ===", runtime_section]
    payload = "\n".join(rows) + "\n"
    response = HttpResponse(payload, content_type="text/plain; charset=utf-8")
    response["Cache-Control"] = "no-store, private"
    response["X-Content-Type-Options"] = "nosniff"
    if request.GET.get("baixar") == "1":
        filename = f"alece-diagnostico-{now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
