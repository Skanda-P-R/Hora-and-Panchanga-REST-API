from __future__ import annotations

import json
import pytest
from hora_server.auth import add_user, reset_device, verify_token

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




def test_api_key_fallback(client, monkeypatch, bengaluru_query):
    # Mock HORA_API_KEY environment variable
    monkeypatch.setenv("HORA_API_KEY", "super-secret-key")
    
    headers = {"X-API-Key": "super-secret-key"}
    response = client.get("/api/v1/panchanga", query_string=begaluru_query_str(bengaluru_query), headers=headers)
    assert response.status_code == 200


def test_google_login_lifecycle(client, clean_users_store, bengaluru_query):
    # 1. Google login with new email (auto-registers account on the fly) -> 200 OK
    response = client.post("/api/v1/auth/google-login", json={
        "idToken": "mock_token_new_user@gmail.com",
        "device_uuid": "device-uuid-phone-a"
    })
    assert response.status_code == 200
    res_data = response.get_json()
    token_a = res_data["token"]
    assert res_data["user"]["email"] == "new_user@gmail.com"
    assert len(token_a) == 64

    # 2. Make authenticated request using Device A token
    headers_a = {"Authorization": f"Bearer {token_a}"}
    response = client.get("/api/v1/panchanga", query_string=begaluru_query_str(bengaluru_query), headers=headers_a)
    assert response.status_code == 200

    # 3. Google login again on Device B with same account (Simultaneous Multi-Device support)
    response_b = client.post("/api/v1/auth/google-login", json={
        "idToken": "mock_token_new_user@gmail.com",
        "device_uuid": "device-uuid-tablet-b"
    })
    assert response_b.status_code == 200
    token_b = response_b.get_json()["token"]
    assert token_b != token_a

    # 4. Both Device A & Device B tokens should be valid simultaneously
    headers_b = {"Authorization": f"Bearer {token_b}"}
    response = client.get("/api/v1/panchanga", query_string=begaluru_query_str(bengaluru_query), headers=headers_b)
    assert response.status_code == 200

    response_a_again = client.get("/api/v1/panchanga", query_string=begaluru_query_str(bengaluru_query), headers=headers_a)
    assert response_a_again.status_code == 200




def test_cli_list_users(app, clean_users_store):
    runner = app.test_cli_runner()
    runner.invoke(args=["add-user", "skanda@gmail.com"])
    result = runner.invoke(args=["list-users"])
    assert "skanda@gmail.com" in result.output


def begaluru_query_str(query):
    # Helper to construct clean query string parameters for panchanga
    # avoiding caching issues with mock request contexts
    q = query.copy()
    if "datetime" in q:
        del q["datetime"]
    q["date"] = "2026-07-20"
    return q

