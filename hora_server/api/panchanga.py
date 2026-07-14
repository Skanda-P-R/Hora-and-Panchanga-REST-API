"""Panchanga API routes."""

from flask import Blueprint, jsonify

from hora_server.extensions import cache, limiter

from .common import context, service


blueprint = Blueprint("panchanga", __name__)


@blueprint.get("/panchanga")
@limiter.limit("60 per minute")
@cache.cached(timeout=60, query_string=True)
def get_panchanga():
    return jsonify(service().panchanga(context()))

