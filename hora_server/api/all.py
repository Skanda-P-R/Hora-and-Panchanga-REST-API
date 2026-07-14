"""Aggregate client API route."""

from flask import Blueprint, jsonify

from hora_server.extensions import cache, limiter

from .common import context, service


blueprint = Blueprint("all", __name__)


@blueprint.get("/all")
@limiter.limit("60 per minute")
@cache.cached(timeout=60, query_string=True)
def get_all():
    return jsonify(service().all(context()))

