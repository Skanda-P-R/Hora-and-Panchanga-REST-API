"""Authentication and session management REST API routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from hora_server.auth import login_device_user, logout_user
from hora_server.extensions import limiter
from hora_server.utils.errors import ApiError


blueprint = Blueprint("auth", __name__)


@blueprint.post("/auth/login")
@limiter.limit("10 per minute")
def login():
    """
    Authenticate a user via device_uuid.
    Returns dynamic session token and device_uuid on success.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("request body must be a JSON object", code="invalid_request_body")

    device_uuid = data.get("device_uuid") or data.get("deviceUuid")

    if not device_uuid or not str(device_uuid).strip():
        raise ApiError("device_uuid is required", code="missing_parameter", details={"parameter": "device_uuid"})

    token, user_info = login_device_user(str(device_uuid))

    return jsonify({
        "token": token,
        "device_uuid": user_info["device_uuid"]
    })


@blueprint.post("/auth/logout")
def logout():
    """Revoke the active session token for the requesting device."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1].strip()
        logout_user(token)
    return jsonify({"status": "logged_out"})
