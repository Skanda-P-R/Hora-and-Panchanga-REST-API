"""Kundali API routes."""

from __future__ import annotations

from flask import Blueprint, Response, jsonify, request

from hora_server.render import (
    render_kundali_png,
    render_kundali_svg,
    resolve_chart_style,
)

from .common import context, service


blueprint = Blueprint("kundali", __name__)


@blueprint.get("/kundali")
def get_kundali():
    if "chart_style" in request.args:
        resolve_chart_style(request.args.get("chart_style"))
    return jsonify(service().kundali(context()))


@blueprint.get("/kundali/chart")
def get_kundali_chart():
    chart_style = resolve_chart_style(request.args.get("chart_style"))
    kundali = service().kundali_model(context())
    return Response(
        render_kundali_png(kundali, chart_style),
        mimetype="image/png",
    )


@blueprint.get("/kundali/svg")
def get_kundali_svg():
    chart_style = resolve_chart_style(request.args.get("chart_style"))
    kundali = service().kundali_model(context())
    return Response(
        render_kundali_svg(kundali, chart_style),
        mimetype="image/svg+xml",
    )
