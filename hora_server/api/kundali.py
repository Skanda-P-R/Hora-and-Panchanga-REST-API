"""Kundali API routes."""

from __future__ import annotations

from flask import Blueprint, Response, jsonify, request

from hora_server.render import (
    ChartInfo,
    render_kundali_png,
    render_kundali_svg,
    resolve_chart_style,
)
from hora_server.service import RequestContext

from .common import context, service


blueprint = Blueprint("kundali", __name__)


def chart_info(context: RequestContext) -> ChartInfo:
    instant = context.instant
    return ChartInfo(
        title="Transit Kundali",
        date=instant.date().isoformat(),
        time=instant.strftime("%H:%M:%S %z"),
        location=f"Lat {context.latitude:.6f}, Lon {context.longitude:.6f}",
    )


@blueprint.get("/kundali")
def get_kundali():
    if "chart_style" in request.args:
        resolve_chart_style(request.args.get("chart_style"))
    return jsonify(service().kundali(context()))


@blueprint.get("/kundali/chart")
def get_kundali_chart():
    chart_style = resolve_chart_style(request.args.get("chart_style"))
    request_context = context()
    kundali = service().kundali_model(request_context)
    return Response(
        render_kundali_png(kundali, chart_style, chart_info(request_context)),
        mimetype="image/png",
    )


@blueprint.get("/kundali/svg")
def get_kundali_svg():
    chart_style = resolve_chart_style(request.args.get("chart_style"))
    request_context = context()
    kundali = service().kundali_model(request_context)
    return Response(
        render_kundali_svg(kundali, chart_style, chart_info(request_context)),
        mimetype="image/svg+xml",
    )
