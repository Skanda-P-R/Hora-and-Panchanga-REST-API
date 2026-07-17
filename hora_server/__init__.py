"""Flask application factory for the Hora and Panchanga service."""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime
from typing import Any

from flask import Flask, g, jsonify, request

from hora_server.api import register_api
from hora_server.astronomy import EphemerisEngine, SolarCalculator
from hora_server.config import Config
from hora_server.extensions import cache, limiter
from hora_server.registry import LocationRegistry
from hora_server.service import PanchangaService
from hora_server.utils.errors import register_error_handlers
from hora_server.utils.timezone import TimezoneResolver


def create_app(config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)
    app.json.sort_keys = False
    cache.init_app(app)
    limiter.init_app(app)

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
    default_filename = "test_locations.json" if app.config.get("TESTING") else "locations.json"
    locations_path = os.getenv("LOCATIONS_FILE_PATH") or os.path.join(app.instance_path, default_filename)
    registry = LocationRegistry(locations_path)
    app.extensions["location_registry"] = registry

    service = PanchangaService(
        engine,
        solar,
        TimezoneResolver(),
        default_ayanamsa=app.config["DEFAULT_AYANAMSA"],
        registry=registry,
    )
    app.extensions["panchanga_service"] = service

    register_error_handlers(app)
    register_api(app)

    @app.before_request
    def start_request_timer() -> None:
        g.request_started_at = time.perf_counter()

    @app.after_request
    def add_operational_headers(response):
        cacheable_endpoints = {
            "all.get_all",
            "calendar.get_calendar",
            "calendar.get_day",
            "hora.get_hora",
            "hora.get_planetary_hours",
            "kundali.get_kundali",
            "kundali.get_kundali_chart",
            "kundali.get_kundali_svg",
            "muhurta.get_muhurta",
            "muhurta.get_rahu",
            "panchanga.get_panchanga",
        }
        if request.endpoint in cacheable_endpoints:
            response.headers["Cache-Control"] = "public, max-age=60"
        duration = None
        started_at = getattr(g, "request_started_at", None)
        if started_at is not None:
            duration = round((time.perf_counter() - started_at) * 1000, 3)
        app.logger.info(
            "request_complete",
            extra={
                "endpoint": request.endpoint,
                "duration_ms": duration,
                "status": response.status_code,
            },
        )
        return response

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
