"""Thread-safe passwordless device-bound user authentication and session management."""

from __future__ import annotations

import json
import os
import secrets
import threading
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


def add_user(username: str) -> bool:
    """Add a new user with empty device binding. Returns True if created."""
    if not username or not username.strip():
        raise ValueError("Username cannot be empty")
        
    cleaned_name = username.strip()
    with _auth_lock:
        users = _load_users()
        # Case-insensitive check
        normalized_names = {name.lower(): name for name in users}
        if cleaned_name.lower() in normalized_names:
            return False
            
        users[cleaned_name] = {
            "bound_device_uuid": None,
            "active_token": None
        }
        _save_users(users)
        return True


def remove_user(username: str) -> bool:
    """Remove a user from pre-registration. Returns True if user found and removed."""
    if not username:
        return False
        
    normalized = username.strip().lower()
    with _auth_lock:
        users = _load_users()
        
        target_key = None
        for key in users:
            if key.lower() == normalized:
                target_key = key
                break
                
        if target_key is not None:
            del users[target_key]
            _save_users(users)
            return True
            
        return False


def reset_device(username: str) -> bool:
    """Reset a user's bound device UUID and active token. Returns True if user found."""
    if not username:
        return False
        
    normalized = username.strip().lower()
    with _auth_lock:
        users = _load_users()
        
        target_key = None
        for key in users:
            if key.lower() == normalized:
                target_key = key
                break
                
        if target_key is not None:
            users[target_key]["bound_device_uuid"] = None
            users[target_key]["active_token"] = None
            _save_users(users)
            return True
            
        return False


def login_user(username: str, device_uuid: str) -> str:
    """
    Validate passwordless login and device UUID binding.
    Returns a new active session token, invalidating the old one.
    Raises ApiError if login fails.
    """
    if not username or not username.strip():
        raise ApiError("Username is required", code="missing_parameter", status_code=400)
    if not device_uuid or not device_uuid.strip():
        raise ApiError("Device UUID is required", code="missing_parameter", status_code=400)
        
    cleaned_username = username.strip()
    cleaned_uuid = device_uuid.strip()
    normalized = cleaned_username.lower()
    
    with _auth_lock:
        users = _load_users()
        
        target_key = None
        for key in users:
            if key.lower() == normalized:
                target_key = key
                break
                
        if target_key is None:
            raise ApiError(
                "Username not registered",
                code="username_not_registered",
                status_code=404,
                details={"username": cleaned_username}
            )
            
        user_record = users[target_key]
        bound_uuid = user_record.get("bound_device_uuid")
        
        if bound_uuid is None:
            # First login: Bind the device UUID to this username
            user_record["bound_device_uuid"] = cleaned_uuid
        elif bound_uuid != cleaned_uuid:
            # Device UUID mismatch
            raise ApiError(
                "This account is registered to another device",
                code="device_mismatch",
                status_code=403,
                details={"username": cleaned_username}
            )
            
        # Generate new session token
        token = secrets.token_hex(32)
        user_record["active_token"] = token
        
        users[target_key] = user_record
        _save_users(users)
        return token


def verify_token(token: str) -> bool:
    """Verify if a session token is active for any user."""
    if not token:
        return False
        
    with _auth_lock:
        users = _load_users()
        for user_record in users.values():
            if user_record.get("active_token") == token:
                return True
        return False


def require_session(f):
    """Decorator to enforce that the request contains a valid, active session token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import current_app
        if current_app.config.get("DISABLE_AUTH_FOR_TESTS"):
            return f(*args, **kwargs)
            
        # We also allow global X-API-Key fallback for backward compatibility or direct admin integration
        auth_header = request.headers.get("Authorization")
        api_key = request.headers.get("X-API-Key")
        
        # Check Authorization header first
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1].strip()
            if verify_token(token):
                return f(*args, **kwargs)
            else:
                raise ApiError(
                    "Session has expired or logged in on another device",
                    code="session_expired",
                    status_code=401
                )
                
        # If API key is set in backend environment, check it
        expected_api_key = os.getenv("HORA_API_KEY")
        if expected_api_key and api_key == expected_api_key:
            return f(*args, **kwargs)
            
        raise ApiError(
            "Missing or invalid session credentials",
            code="unauthorized",
            status_code=401
        )
    return decorated
