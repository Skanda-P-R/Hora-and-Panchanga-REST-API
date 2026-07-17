"""Authentication and session management REST API routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from hora_server.auth import login_user
from hora_server.extensions import limiter
from hora_server.utils.errors import ApiError


blueprint = Blueprint("auth", __name__)


@blueprint.post("/auth/login")
@limiter.limit("10 per minute")
def login():
    """
    Authenticate a user via username and device UUID.
    Returns a dynamic session token on success.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("request body must be a JSON object", code="invalid_request_body")

    username = data.get("username")
    device_uuid = data.get("device_uuid")

    if not username or not str(username).strip():
        raise ApiError("username is required", code="missing_parameter", details={"parameter": "username"})
    if not device_uuid or not str(device_uuid).strip():
        raise ApiError("device_uuid is required", code="missing_parameter", details={"parameter": "device_uuid"})

    token = login_user(str(username), str(device_uuid))
    return jsonify({"token": token})
