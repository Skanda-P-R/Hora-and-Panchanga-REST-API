"""Hora API routes."""

from flask import Blueprint, jsonify

from .common import context, service


blueprint = Blueprint("hora", __name__)


@blueprint.get("/hora")
def get_hora():
    return jsonify(service().hora(context()))


@blueprint.get("/planetary-hours")
def get_planetary_hours():
    return jsonify(service().planetary_hours(context()))

