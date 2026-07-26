"""Thread-safe user authentication and session management supporting Google Sign-In and Email Whitelisting."""

from __future__ import annotations

import json
import os
import secrets
import threading
import urllib.request
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from flask import current_app, request

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


def add_user(identifier: str) -> bool:
    """Pre-register a new user email or username in the whitelist. Returns True if created."""
    if not identifier or not identifier.strip():
        raise ValueError("Identifier cannot be empty")
        
    cleaned = identifier.strip()
    normalized = cleaned.lower()
    with _auth_lock:
        users = _load_users()
        normalized_keys = {k.lower(): k for k in users}
        if normalized in normalized_keys:
            return False
            
        users[cleaned] = {
            "google_sub": None,
            "email": cleaned,
            "name": None,
            "picture": None,
            "created_at": datetime.now(UTC).isoformat(),
            "last_login": None,
            "active_tokens": [],
            "bound_device_uuid": None,
            "active_token": None
        }
        _save_users(users)
        return True


def remove_user(identifier: str) -> bool:
    """Remove a user from pre-registration. Returns True if found and removed."""
    if not identifier:
        return False
        
    normalized = identifier.strip().lower()
    with _auth_lock:
        users = _load_users()
        
        target_key = None
        for key in users:
            if key.lower() == normalized or (isinstance(users[key], dict) and users[key].get("email", "").lower() == normalized):
                target_key = key
                break
                
        if target_key is not None:
            del users[target_key]
            _save_users(users)
            return True
            
        return False


def reset_device(identifier: str) -> bool:
    """Reset a user's bound device UUID and clear active tokens. Returns True if user found."""
    if not identifier:
        return False
        
    normalized = identifier.strip().lower()
    with _auth_lock:
        users = _load_users()
        
        target_key = None
        for key in users:
            if key.lower() == normalized or (isinstance(users[key], dict) and users[key].get("email", "").lower() == normalized):
                target_key = key
                break
                
        if target_key is not None:
            users[target_key]["bound_device_uuid"] = None
            users[target_key]["active_token"] = None
            users[target_key]["active_tokens"] = []
            _save_users(users)
            return True
            
        return False


def list_users() -> list[dict]:
    """Return a list of all pre-registered users and their status."""
    with _auth_lock:
        users = _load_users()
        result = []
        for key, record in users.items():
            if isinstance(record, dict):
                tokens = record.get("active_tokens", [])
                if record.get("active_token") and record.get("active_token") not in tokens:
                    tokens.append(record.get("active_token"))
                result.append({
                    "identifier": key,
                    "email": record.get("email", key),
                    "google_sub": record.get("google_sub"),
                    "name": record.get("name"),
                    "last_login": record.get("last_login"),
                    "active_sessions": len([t for t in tokens if t])
                })
        return result


def verify_google_id_token(id_token: str, web_client_id: str | None = None) -> dict:
    """
    Verify a Google ID Token (JWT) and extract user info.
    Supports mock tokens during testing.
    """
    if not id_token or not id_token.strip():
        raise ApiError("Google ID Token is required", code="missing_parameter", status_code=400)

    id_token = id_token.strip()

    # Fast path for testing environments
    if current_app.config.get("TESTING") and (id_token.startswith("mock_token_") or id_token.startswith("test_token_")):
        email = id_token.replace("mock_token_", "").replace("test_token_", "")
        if "@" not in email:
            email = f"{email}@gmail.com"
        return {
            "email": email,
            "sub": f"google_sub_{email}",
            "name": email.split("@")[0].title(),
            "picture": "https://lh3.googleusercontent.com/a/default_avatar"
        }

    # Attempt Google Auth library if installed
    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests

        claims = google_id_token.verify_oauth2_token(
            id_token, google_requests.Request(), audience=web_client_id or None
        )
        email = claims.get("email")
        if not email or claims.get("email_verified") is False:
            raise ApiError("Google account email not verified", code="email_not_verified", status_code=401)
        return {
            "email": email,
            "sub": claims.get("sub"),
            "name": claims.get("name"),
            "picture": claims.get("picture")
        }
    except ApiError:
        raise
    except ImportError:
        # Fallback to Google TokenInfo API if google-auth library isn't installed
        try:
            url = f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
            req = urllib.request.Request(url, headers={"User-Agent": "HoraServer/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    claims = json.loads(resp.read().decode("utf-8"))
                    email = claims.get("email")
                    if not email or claims.get("email_verified") == "false":
                        raise ApiError("Google account email not verified", code="email_not_verified", status_code=401)
                    if web_client_id and claims.get("aud") != web_client_id:
                        raise ApiError("Google ID Token audience mismatch", code="invalid_audience", status_code=401)
                    return {
                        "email": email,
                        "sub": claims.get("sub"),
                        "name": claims.get("name"),
                        "picture": claims.get("picture")
                    }
        except ApiError:
            raise
        except Exception as err:
            raise ApiError(f"Invalid or expired Google ID Token: {err}", code="invalid_google_token", status_code=401) from err
    except Exception as err:
        raise ApiError(f"Invalid or expired Google ID Token: {err}", code="invalid_google_token", status_code=401) from err


def login_google_user(id_token: str, device_uuid: str | None = None, web_client_id: str | None = None) -> tuple[str, dict]:
    """
    Authenticate a user via Google ID Token against the email whitelist.
    Returns (session_token, user_info).
    """
    claims = verify_google_id_token(id_token, web_client_id)
    email = claims["email"].strip()
    normalized_email = email.lower()

    with _auth_lock:
        users = _load_users()

        target_key = None
        for key in users:
            if key.lower() == normalized_email or (isinstance(users[key], dict) and users[key].get("email", "").lower() == normalized_email):
                target_key = key
                break

        if target_key is None:
            raise ApiError(
                "Email address not pre-approved. Contact administrator for access.",
                code="email_not_authorized",
                status_code=403,
                details={"email": email}
            )

        user_record = users[target_key]
        if not isinstance(user_record, dict):
            user_record = {}

        # Update user profile metadata
        user_record["google_sub"] = claims.get("sub") or user_record.get("google_sub")
        user_record["email"] = email
        user_record["name"] = claims.get("name") or user_record.get("name")
        user_record["picture"] = claims.get("picture") or user_record.get("picture")
        user_record["last_login"] = datetime.now(UTC).isoformat()
        if device_uuid:
            user_record["last_device_uuid"] = device_uuid

        # Generate new session token
        token = secrets.token_hex(32)
        active_tokens = user_record.get("active_tokens", [])
        if not isinstance(active_tokens, list):
            active_tokens = []
        active_tokens.append(token)
        user_record["active_tokens"] = active_tokens
        user_record["active_token"] = token  # Backwards compatibility

        users[target_key] = user_record
        _save_users(users)

        user_info = {
            "email": email,
            "name": user_record.get("name"),
            "picture": user_record.get("picture")
        }
        return token, user_info



def verify_token(token: str) -> bool:
    """Verify if a session token is active for any user."""
    if not token:
        return False
        
    with _auth_lock:
        users = _load_users()
        for user_record in users.values():
            if not isinstance(user_record, dict):
                continue
            active_tokens = user_record.get("active_tokens", [])
            if isinstance(active_tokens, list) and token in active_tokens:
                return True
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
                    status_code=401
                )
                
        expected_api_key = os.getenv("HORA_API_KEY")
        if expected_api_key and api_key == expected_api_key:
            return f(*args, **kwargs)
            
        raise ApiError(
            "Missing or invalid session credentials",
            code="unauthorized",
            status_code=401
        )
    return decorated

