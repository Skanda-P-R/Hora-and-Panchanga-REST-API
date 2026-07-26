"""Flask application factory for the Hora and Panchanga service."""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime
from typing import Any

import click
from flask import Flask, g, jsonify, request

from hora_server.api import register_api
from hora_server.astronomy import EphemerisEngine, SolarCalculator
from hora_server.auth import init_auth_store, add_user, reset_device, remove_user, list_users
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

    default_users_filename = "test_users.json" if app.config.get("TESTING") else "users.json"
    users_path = os.getenv("USERS_FILE_PATH") or os.path.join(app.instance_path, default_users_filename)
    init_auth_store(users_path)

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

    @app.cli.command("add-user")
    @click.argument("identifier")
    def add_user_command(identifier):
        """Pre-register a new email address or username for access whitelist."""
        success = add_user(identifier)
        if success:
            click.echo(f"User '{identifier}' pre-registered successfully.")
        else:
            click.echo(f"Error: User '{identifier}' already exists.")

    @app.cli.command("reset-device")
    @click.argument("identifier")
    def reset_device_command(identifier):
        """Reset the device binding and clear sessions for a user."""
        success = reset_device(identifier)
        if success:
            click.echo(f"Device binding for user '{identifier}' reset successfully.")
        else:
            click.echo(f"Error: User '{identifier}' not found.")

    @app.cli.command("remove-user")
    @click.argument("identifier")
    def remove_user_command(identifier):
        """Remove a user from pre-registration whitelist and invalidate their session."""
        success = remove_user(identifier)
        if success:
            click.echo(f"User '{identifier}' removed successfully.")
        else:
            click.echo(f"Error: User '{identifier}' not found.")

    @app.cli.command("list-users")
    def list_users_command():
        """List all pre-registered users in the whitelist."""
        users = list_users()
        if not users:
            click.echo("No users pre-registered.")
            return
        click.echo(f"Found {len(users)} pre-registered user(s):")
        for u in users:
            click.echo(f" - {u['email']} (Google Sub: {u['google_sub'] or 'Not activated'}, Active sessions: {u['active_sessions']})")

    return app

