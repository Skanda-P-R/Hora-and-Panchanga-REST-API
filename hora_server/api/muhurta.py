"""Muhurta and Rahu Kalam API routes."""

from flask import Blueprint, jsonify

from hora_server.extensions import cache, limiter

from .common import context, service


blueprint = Blueprint("muhurta", __name__)


@blueprint.get("/muhurta")
@limiter.limit("60 per minute")
@cache.cached(timeout=60, query_string=True)
def get_muhurta():
    return jsonify(service().muhurta(context()))


@blueprint.get("/rahu")
@limiter.limit("60 per minute")
@cache.cached(timeout=60, query_string=True)
def get_rahu():
    return jsonify(service().rahu(context()))

