"""Solar-day and daily transition API routes."""

from flask import Blueprint, jsonify

from hora_server.extensions import cache, limiter

from .common import context, service


blueprint = Blueprint("calendar", __name__)


@blueprint.get("/day")
@limiter.limit("60 per minute")
@cache.cached(timeout=60, query_string=True)
def get_day():
    return jsonify(service().day(context()))


@blueprint.get("/calendar")
@limiter.limit("60 per minute")
@cache.cached(timeout=60, query_string=True)
def get_calendar():
    return jsonify(service().calendar(context()))

