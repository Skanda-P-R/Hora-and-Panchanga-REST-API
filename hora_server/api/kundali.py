"""Kundali API routes."""

from __future__ import annotations

from flask import Blueprint, Response, jsonify, request

from hora_server.auth import require_session
from hora_server.extensions import cache, limiter
from hora_server.render import (
    ChartInfo,
    render_kundali_png,
    render_kundali_svg,
    resolve_chart_language,
    resolve_chart_style,
)
from hora_server.service import RequestContext

from .common import context, service


blueprint = Blueprint("kundali", __name__)


def chart_info(context: RequestContext, language: str = "en") -> ChartInfo:
    instant = context.instant
    return ChartInfo(
        title="ಗೋಚಾರ ಕುಂಡಲಿ" if language == "kan" else "Transit Kundali",
        date=instant.date().isoformat(),
        time=instant.strftime("%H:%M:%S %z"),
        location=f"Lat {context.latitude:.6f}, Lon {context.longitude:.6f}",
    )


def birth_chart_info(context: RequestContext, language: str = "en", name: str | None = None) -> ChartInfo:
    instant = context.instant
    if language == "kan":
        title = "ಜನನ ಕುಂಡಲಿ"
        if name:
            title = f"{name} - {title}"
    else:
        title = "Janma Kundali"
        if name:
            title = f"{name} - {title}"
    return ChartInfo(
        title=title,
        date=instant.date().isoformat(),
        time=instant.strftime("%H:%M:%S %z"),
        location=f"Lat {context.latitude:.6f}, Lon {context.longitude:.6f}",
    )


@blueprint.get("/kundali")
@require_session
@limiter.limit("60 per minute")
@cache.cached(timeout=60, query_string=True)
def get_kundali():
    if "chart_style" in request.args:
        resolve_chart_style(request.args.get("chart_style"))
    return jsonify(service().kundali(context()))


@blueprint.get("/kundali/chart")
@require_session
@limiter.limit("60 per minute")
@cache.cached(timeout=60, query_string=True)
def get_kundali_chart():
    chart_style = resolve_chart_style(request.args.get("chart_style"))
    language = resolve_chart_language(request.args.get("lang"))
    request_context = context()
    kundali = service().kundali_model(request_context)
    return Response(
        render_kundali_png(
            kundali,
            chart_style,
            chart_info(request_context, language),
            language,
        ),
        mimetype="image/png",
    )


@blueprint.get("/kundali/svg")
@require_session
@limiter.limit("60 per minute")
@cache.cached(timeout=60, query_string=True)
def get_kundali_svg():
    chart_style = resolve_chart_style(request.args.get("chart_style"))
    language = resolve_chart_language(request.args.get("lang"))
    request_context = context()
    kundali = service().kundali_model(request_context)
    return Response(
        render_kundali_svg(
            kundali,
            chart_style,
            chart_info(request_context, language),
            language,
        ),
        mimetype="image/svg+xml",
    )


@blueprint.get("/kundali/birth")
@require_session
@limiter.limit("60 per minute")
@cache.cached(timeout=60, query_string=True)
def get_kundali_birth():
    if "chart_style" in request.args:
        resolve_chart_style(request.args.get("chart_style"))
    result = service().kundali(context())
    name = request.args.get("name")
    if name:
        result["name"] = name.strip()
    return jsonify(result)


@blueprint.get("/kundali/birth/chart")
@require_session
@limiter.limit("60 per minute")
@cache.cached(timeout=60, query_string=True)
def get_kundali_birth_chart():
    chart_style = resolve_chart_style(request.args.get("chart_style"))
    language = resolve_chart_language(request.args.get("lang"))
    name = request.args.get("name")
    request_context = context()
    kundali = service().kundali_model(request_context)
    return Response(
        render_kundali_png(
            kundali,
            chart_style,
            birth_chart_info(request_context, language, name),
            language,
        ),
        mimetype="image/png",
    )


@blueprint.get("/kundali/birth/svg")
@require_session
@limiter.limit("60 per minute")
@cache.cached(timeout=60, query_string=True)
def get_kundali_birth_svg():
    chart_style = resolve_chart_style(request.args.get("chart_style"))
    language = resolve_chart_language(request.args.get("lang"))
    name = request.args.get("name")
    request_context = context()
    kundali = service().kundali_model(request_context)
    return Response(
        render_kundali_svg(
            kundali,
            chart_style,
            birth_chart_info(request_context, language, name),
            language,
        ),
        mimetype="image/svg+xml",
    )
