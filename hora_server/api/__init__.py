"""Versioned REST API blueprint registration."""

from __future__ import annotations

from flask import Flask

from .all import blueprint as all_blueprint
from .calendar import blueprint as calendar_blueprint
from .hora import blueprint as hora_blueprint
from .muhurta import blueprint as muhurta_blueprint
from .panchanga import blueprint as panchanga_blueprint


def register_api(app: Flask) -> None:
    prefix = "/api/v1"
    for blueprint in (
        hora_blueprint,
        panchanga_blueprint,
        calendar_blueprint,
        muhurta_blueprint,
        all_blueprint,
    ):
        app.register_blueprint(blueprint, url_prefix=prefix)

