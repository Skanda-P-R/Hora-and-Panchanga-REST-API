"""Aggregate client API route."""

from flask import Blueprint, jsonify

from .common import context, service


blueprint = Blueprint("all", __name__)


@blueprint.get("/all")
def get_all():
    return jsonify(service().all(context()))

