from __future__ import annotations

import json
import pytest
from hora_server.auth import add_user, reset_device, verify_token, login_user
from hora_server.extensions import cache


@pytest.fixture(autouse=True)
def enable_auth(app):
    """Enable authentication checks during session security tests."""
    app.config["DISABLE_AUTH_FOR_TESTS"] = False
    yield
    app.config["DISABLE_AUTH_FOR_TESTS"] = True


@pytest.fixture()
def clean_users_store(app):
    """Reset the users.json store before each test."""
    auth_store = app.extensions.get("location_registry")  # Not actual auth, let's get registry path
    # Actually, let's use the private auth store lock
    from hora_server.auth import _auth_lock, _save_users
    with _auth_lock:
        _save_users({})
    cache.clear()
    yield


def test_cli_add_user_and_reset(app, clean_users_store):
    runner = app.test_cli_runner()
    
    # 1. Add user via CLI
    result = runner.invoke(args=["add-user", "test_skanda"])
    assert "pre-registered successfully" in result.output
    
    # 2. Add duplicate user
    result = runner.invoke(args=["add-user", "test_skanda"])
    assert "already exists" in result.output

    # 3. Reset device via CLI
    result = runner.invoke(args=["reset-device", "test_skanda"])
    assert "reset successfully" in result.output

    # 4. Reset non-existing user
    result = runner.invoke(args=["reset-device", "unknown_user"])
    assert "not found" in result.output

    # 5. Remove user via CLI
    result = runner.invoke(args=["remove-user", "test_skanda"])
    assert "removed successfully" in result.output

    # 6. Remove non-existing user
    result = runner.invoke(args=["remove-user", "unknown_user"])
    assert "not found" in result.output


def test_unauthenticated_requests(client):
    # Requests without headers should return 401
    response = client.get("/api/v1/panchanga")
    assert response.status_code == 401
    data = response.get_json()
    assert data["error"]["code"] == "unauthorized"


def test_session_lifecycle_and_uuid_binding(client, clean_users_store, bengaluru_query):
    # 1. Pre-register the username
    assert add_user("skanda") is True

    # 2. Attempt login with non-existent user
    login_payload = {"username": "unknown", "device_uuid": "device-123"}
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "username_not_registered"

    # 3. First login (device binding activation)
    login_payload = {"username": "skanda", "device_uuid": "uuid-phone-a"}
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    token = response.get_json()["token"]
    assert len(token) == 64

    # 4. Make authenticated request with correct token
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/panchanga", query_string=begaluru_query_str(bengaluru_query), headers=headers)
    assert response.status_code == 200

    # 5. Make request with invalid token
    headers_invalid = {"Authorization": "Bearer badtoken"}
    response = client.get("/api/v1/panchanga", query_string=begaluru_query_str(bengaluru_query), headers=headers_invalid)
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "session_expired"

    # 6. Attempt login from another device (should be rejected due to UUID mismatch)
    login_payload_b = {"username": "skanda", "device_uuid": "uuid-phone-b"}
    response = client.post("/api/v1/auth/login", json=login_payload_b)
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "device_mismatch"

    # 7. Reset the device binding
    assert reset_device("skanda") is True

    # 8. Log in from Phone B (should succeed now and bind Phone B)
    response = client.post("/api/v1/auth/login", json=login_payload_b)
    assert response.status_code == 200
    token_b = response.get_json()["token"]
    assert token_b != token

    # 9. Verify Phone A's token is now invalidated (Single Active Session check)
    headers_a = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/panchanga", query_string=begaluru_query_str(bengaluru_query), headers=headers_a)
    assert response.status_code == 401


def test_api_key_fallback(client, monkeypatch, bengaluru_query):
    # Mock HORA_API_KEY environment variable
    monkeypatch.setenv("HORA_API_KEY", "super-secret-key")
    
    headers = {"X-API-Key": "super-secret-key"}
    response = client.get("/api/v1/panchanga", query_string=begaluru_query_str(bengaluru_query), headers=headers)
    assert response.status_code == 200


def begaluru_query_str(query):
    # Helper to construct clean query string parameters for panchanga
    # avoiding caching issues with mock request contexts
    q = query.copy()
    if "datetime" in q:
        del q["datetime"]
    q["date"] = "2026-07-20"
    return q
