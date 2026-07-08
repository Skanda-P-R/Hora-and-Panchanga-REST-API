"""Panchanga API routes."""

from flask import Blueprint, jsonify

from .common import context, service


blueprint = Blueprint("panchanga", __name__)


@blueprint.get("/panchanga")
def get_panchanga():
    return jsonify(service().panchanga(context()))

