"""API endpoints for managing saved locations and favorite cities."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from hora_server.auth import require_session
from hora_server.extensions import limiter
from hora_server.registry import LocationRegistry
from hora_server.utils.errors import ApiError
from hora_server.utils.timezone import TimezoneResolver
from typing import Any


blueprint = Blueprint("locations", __name__)


def registry() -> LocationRegistry:
    """Helper to access the LocationRegistry instance from extensions."""
    return current_app.extensions["location_registry"]


def validate_coordinates(lat_val: Any, lon_val: Any) -> tuple[float, float]:
    """Helper to validate latitude and longitude values."""
    try:
        latitude = float(lat_val)
    except (ValueError, TypeError) as exc:
        raise ApiError(
            "latitude must be a number",
            code="invalid_parameter",
            details={"parameter": "latitude", "value": str(lat_val)},
        ) from exc

    try:
        longitude = float(lon_val)
    except (ValueError, TypeError) as exc:
        raise ApiError(
            "longitude must be a number",
            code="invalid_parameter",
            details={"parameter": "longitude", "value": str(lon_val)},
        ) from exc

    if not -90 <= latitude <= 90:
        raise ApiError(
            "latitude must be between -90 and 90",
            code="invalid_parameter",
            details={"parameter": "latitude", "value": latitude},
        )
    if not -180 <= longitude <= 180:
        raise ApiError(
            "longitude must be between -180 and 180",
            code="invalid_parameter",
            details={"parameter": "longitude", "value": longitude},
        )

    return round(latitude, 4), round(longitude, 4)


@blueprint.get("/locations")
@require_session
@limiter.limit("60 per minute")
def get_locations():
    """Retrieve all saved locations."""
    return jsonify(registry().get_all("saved_locations"))


@blueprint.post("/locations")
@require_session
@limiter.limit("30 per minute")
def save_location():
    """Create or update a saved location."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("request body must be a JSON object", code="invalid_request_body")

    name = data.get("name")
    if not name or not str(name).strip():
        raise ApiError("name is required", code="missing_parameter", details={"parameter": "name"})

    latitude, longitude = validate_coordinates(data.get("latitude"), data.get("longitude"))
    
    # Resolve timezone
    tz_resolver = TimezoneResolver()
    timezone = tz_resolver.resolve(latitude, longitude, data.get("timezone")).key

    entry_data = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
        "description": str(data.get("description", "")).strip()
    }
    
    registry().add_entry("saved_locations", str(name), entry_data)
    return jsonify({"status": "saved", "name": str(name).strip()}), 201


@blueprint.delete("/locations/<name>")
@require_session
@limiter.limit("30 per minute")
def delete_location(name: str):
    """Delete a saved location."""
    deleted = registry().delete_entry("saved_locations", name)
    if not deleted:
        raise ApiError(
            f"Location '{name}' not found",
            code="location_not_found",
            status_code=404,
            details={"name": name}
        )
    return jsonify({"status": "deleted", "name": name})


@blueprint.get("/favorites")
@require_session
@limiter.limit("60 per minute")
def get_favorites():
    """Retrieve all favorite cities."""
    return jsonify(registry().get_all("favorite_cities"))


@blueprint.post("/favorites")
@require_session
@limiter.limit("30 per minute")
def save_favorite():
    """Create or update a favorite city."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("request body must be a JSON object", code="invalid_request_body")

    name = data.get("name")
    if not name or not str(name).strip():
        raise ApiError("name is required", code="missing_parameter", details={"parameter": "name"})

    latitude, longitude = validate_coordinates(data.get("latitude"), data.get("longitude"))
    
    # Resolve timezone
    tz_resolver = TimezoneResolver()
    timezone = tz_resolver.resolve(latitude, longitude, data.get("timezone")).key

    entry_data = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
        "country": str(data.get("country", "")).strip()
    }
    
    registry().add_entry("favorite_cities", str(name), entry_data)
    return jsonify({"status": "saved", "name": str(name).strip()}), 201


@blueprint.delete("/favorites/<name>")
@require_session
@limiter.limit("30 per minute")
def delete_favorite(name: str):
    """Delete a favorite city."""
    deleted = registry().delete_entry("favorite_cities", name)
    if not deleted:
        raise ApiError(
            f"Favorite city '{name}' not found",
            code="city_not_found",
            status_code=404,
            details={"name": name}
        )
    return jsonify({"status": "deleted", "name": name})
