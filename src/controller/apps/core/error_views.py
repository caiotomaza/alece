# SPDX-License-Identifier: GPL-3.0-only
"""Paginas HTTP de erro independentes do banco e do layout autenticado."""
import html
import logging
import uuid
from django.http import HttpResponse
from django.template.loader import render_to_string

logger = logging.getLogger("alece.errors")

_DESCRIPTIONS = {
    400: ("Requisicao invalida", "A solicitacao nao pode ser processada."),
    403: ("Acesso nao permitido", "Sua conta nao tem autorizacao para realizar esta operacao."),
    404: ("Pagina nao encontrada", "O endereco solicitado nao existe ou foi movido."),
    500: ("Erro interno do servidor", "Ocorreu uma falha inesperada ao processar esta solicitacao."),
    503: ("Servico temporariamente indisponivel", "O servico ou o banco de dados esta temporariamente indisponivel."),
}


def _render_error(request, status):
    # Nao consultar banco, sessao ou middleware de contexto. Deve funcionar em 500.
    incident = uuid.uuid4().hex[:12].upper()
    heading, description = _DESCRIPTIONS[status]
    if status >= 500:
        logger.error("Falha HTTP %s | incidente=%s", status, incident)
    ctx = {"status": status, "heading": heading, "description": description,
           "incident": incident, "path": str(getattr(request, "path", "/"))[:180]}
    try:
        body = render_to_string("core/error_page.html", ctx)
    except Exception:
        logger.exception("Falha ao renderizar pagina de erro %s", status)
        body = ('<!doctype html><html lang="pt-BR"><meta charset="utf-8">'
                f'<title>Erro {status} | ALECE</title><body><h1>Erro {status}</h1>'
                f'<p>{html.escape(heading)}</p><a href="/">Inicio</a></body></html>')
    response = HttpResponse(body, status=status, content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "no-store"
    return response


def error400(request, exception):
    return _render_error(request, 400)


def error403(request, exception):
    return _render_error(request, 403)


def error404(request, exception):
    return _render_error(request, 404)


def error500(request):
    return _render_error(request, 500)
