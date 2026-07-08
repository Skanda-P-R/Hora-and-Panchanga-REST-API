"""Muhurta and Rahu Kalam API routes."""

from flask import Blueprint, jsonify

from .common import context, service


blueprint = Blueprint("muhurta", __name__)


@blueprint.get("/muhurta")
def get_muhurta():
    return jsonify(service().muhurta(context()))


@blueprint.get("/rahu")
def get_rahu():
    return jsonify(service().rahu(context()))

