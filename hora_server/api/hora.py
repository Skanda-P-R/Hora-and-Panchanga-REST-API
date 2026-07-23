"""Hora API routes."""

from flask import Blueprint, jsonify

from hora_server.auth import require_session
from hora_server.extensions import cache, limiter

from .common import context, service


blueprint = Blueprint("hora", __name__)


@blueprint.get("/hora")
@require_session
@limiter.limit("60 per minute")
@cache.cached(timeout=60, query_string=True)
def get_hora():
    return jsonify(service().hora(context()))


@blueprint.get("/planetary-hours")
@require_session
@limiter.limit("60 per minute")
@cache.cached(timeout=60, query_string=True)
def get_planetary_hours():
    return jsonify(service().planetary_hours(context()))

