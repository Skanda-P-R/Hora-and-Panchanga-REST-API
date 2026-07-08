"""Solar-day and daily transition API routes."""

from flask import Blueprint, jsonify

from .common import context, service


blueprint = Blueprint("calendar", __name__)


@blueprint.get("/day")
def get_day():
    return jsonify(service().day(context()))


@blueprint.get("/calendar")
def get_calendar():
    return jsonify(service().calendar(context()))

