"""Thread-safe user authentication and session management supporting Device UUID authentication."""

from __future__ import annotations

import json
import os
import secrets
import threading
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from flask import request

from hora_server.utils.errors import ApiError

# Thread lock for auth file operations
_auth_lock = threading.RLock()
_users_filepath: Path | None = None


def init_auth_store(filepath: str | Path) -> None:
    """Initialize the path for users database and ensure the file exists."""
    global _users_filepath
    with _auth_lock:
        _users_filepath = Path(filepath)
        if not _users_filepath.exists():
            _users_filepath.parent.mkdir(parents=True, exist_ok=True)
            _save_users({})


def _load_users() -> dict:
    """Load the users file. Assumes lock is held."""
    if _users_filepath is None:
        return {}
    try:
        with open(_users_filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_users(data: dict) -> None:
    """Save the users file. Assumes lock is held."""
    if _users_filepath is None:
        return
    temp_file = _users_filepath.with_suffix(".tmp")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        temp_file.replace(_users_filepath)
    except Exception:
        if temp_file.exists():
            temp_file.unlink()
        raise


def login_device_user(device_uuid: str) -> tuple[str, dict]:
    """
    Authenticate a user via device_uuid.
    Generates a new active authentication token and stores/updates the device record in users.json.
    Re-logging in on the same device_uuid updates its active token.
    Returns (session_token, user_info).
    """
    if not device_uuid or not str(device_uuid).strip():
        raise ApiError("device_uuid is required", code="missing_parameter", status_code=400)

    clean_uuid = str(device_uuid).strip()
    token = secrets.token_hex(32)

    with _auth_lock:
        users = _load_users()
        existing = users.get(clean_uuid)
        created_at = (
            existing.get("created_at")
            if isinstance(existing, dict) and existing.get("created_at")
            else datetime.now(UTC).isoformat()
        )

        users[clean_uuid] = {
            "device_uuid": clean_uuid,
            "active_token": token,
            "created_at": created_at,
            "last_login": datetime.now(UTC).isoformat(),
        }
        _save_users(users)

    user_info = {
        "device_uuid": clean_uuid,
    }
    return token, user_info


def logout_user(token: str) -> bool:
    """
    Revoke a specific session token upon logout by deleting the matching device entry from users.json.
    Returns True if found and deleted, False otherwise.
    """
    if not token or not str(token).strip():
        return False

    clean_token = str(token).strip()
    with _auth_lock:
        users = _load_users()
        to_delete = None
        for device_uuid, record in users.items():
            if isinstance(record, dict) and record.get("active_token") == clean_token:
                to_delete = device_uuid
                break

        if to_delete is not None:
            del users[to_delete]
            _save_users(users)
            return True
        return False


def verify_token(token: str) -> bool:
    """Verify if a session token is active for any registered device."""
    if not token or not str(token).strip():
        return False

    clean_token = str(token).strip()
    with _auth_lock:
        users = _load_users()
        for record in users.values():
            if isinstance(record, dict) and record.get("active_token") == clean_token:
                return True
        return False


def get_active_users_count() -> int:
    """Return the total number of active users (registered device entries with an active token)."""
    with _auth_lock:
        users = _load_users()
        count = 0
        for record in users.values():
            if isinstance(record, dict) and record.get("active_token"):
                count += 1
        return count


def require_session(f):
    """Decorator to enforce that the request contains a valid, active session token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import current_app
        if current_app.config.get("DISABLE_AUTH_FOR_TESTS"):
            return f(*args, **kwargs)

        auth_header = request.headers.get("Authorization")
        api_key = request.headers.get("X-API-Key")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1].strip()
            if verify_token(token):
                return f(*args, **kwargs)
            else:
                raise ApiError(
                    "Session has expired or logged in on another device",
                    code="session_expired",
                    status_code=401,
                )

        expected_api_key = os.getenv("HORA_API_KEY")
        if expected_api_key and api_key == expected_api_key:
            return f(*args, **kwargs)

        raise ApiError(
            "Missing or invalid session credentials",
            code="unauthorized",
            status_code=401,
        )
    return decorated
