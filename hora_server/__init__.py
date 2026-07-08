"""Flask application factory for the Hora and Panchanga service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from flask import Flask, jsonify

from hora_server.api import register_api
from hora_server.astronomy import EphemerisEngine, SolarCalculator
from hora_server.config import Config
from hora_server.service import PanchangaService
from hora_server.utils.errors import register_error_handlers
from hora_server.utils.timezone import TimezoneResolver


def create_app(config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)
    app.json.sort_keys = False

    engine = EphemerisEngine(
        ephemeris_path=app.config.get("EPHEMERIS_PATH"),
        strict_swiss=bool(app.config.get("STRICT_SWISS_EPHEMERIS")),
    )
    solar = SolarCalculator(
        engine,
        elevation_meters=float(app.config["OBSERVER_ELEVATION_METERS"]),
        pressure_hpa=float(app.config["ATMOSPHERIC_PRESSURE_HPA"]),
        temperature_c=float(app.config["ATMOSPHERIC_TEMPERATURE_C"]),
    )
    service = PanchangaService(
        engine,
        solar,
        TimezoneResolver(),
        default_ayanamsa=app.config["DEFAULT_AYANAMSA"],
    )
    app.extensions["panchanga_service"] = service

    register_error_handlers(app)
    register_api(app)

    @app.get("/health")
    def health():
        ayanamsa = engine.resolve_ayanamsa(app.config["DEFAULT_AYANAMSA"])
        probe = engine.positions(datetime.now(UTC), ayanamsa)
        return jsonify(
            {
                "status": "ok",
                "service": "hora-panchanga",
                "swiss_ephemeris_version": engine.version,
                "ephemeris_backend": probe.ephemeris,
                "ephemeris_ready": probe.ephemeris == "swiss",
            }
        )

    @app.get("/")
    def index():
        return jsonify(
            {
                "service": "Hora & Panchanga REST API",
                "version": "v1",
                "health": "/health",
                "endpoint_prefix": "/api/v1",
            }
        )

    return app
