"""Authentication and session management REST API routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from hora_server.auth import login_google_user, logout_user
from hora_server.extensions import limiter
from hora_server.utils.errors import ApiError


blueprint = Blueprint("auth", __name__)


@blueprint.post("/auth/google-login")
@limiter.limit("10 per minute")
def google_login():
    """
    Authenticate a user via Google ID Token against pre-approved email whitelist.
    Returns dynamic session token and user profile on success.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("request body must be a JSON object", code="invalid_request_body")

    id_token = data.get("idToken") or data.get("id_token")
    device_uuid = data.get("device_uuid") or data.get("deviceUuid")

    if not id_token or not str(id_token).strip():
        raise ApiError("idToken is required", code="missing_parameter", details={"parameter": "idToken"})

    from flask import current_app
    web_client_id = current_app.config.get("GOOGLE_WEB_CLIENT_ID")
    token, user_info = login_google_user(
        str(id_token),
        device_uuid=str(device_uuid) if device_uuid else None,
        web_client_id=web_client_id
    )

    return jsonify({
        "token": token,
        "user": user_info
    })


@blueprint.post("/auth/logout")
def logout():
    """Revoke the active session token for the requesting device."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1].strip()
        logout_user(token)
    return jsonify({"status": "logged_out"})



