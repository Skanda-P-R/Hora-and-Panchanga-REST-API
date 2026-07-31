from __future__ import annotations

import json
import pytest
from hora_server.auth import verify_token, get_active_users_count
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
    from hora_server.auth import _auth_lock, _save_users
    with _auth_lock:
        _save_users({})
    cache.clear()
    yield


def test_device_login_missing_uuid(client):
    # Request without device_uuid should return 400
    response = client.post("/api/v1/auth/login", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert data["error"]["code"] == "missing_parameter"


def test_device_login_lifecycle(client, clean_users_store, bengaluru_query):
    # 1. Login with Device A -> 200 OK
    response = client.post("/api/v1/auth/login", json={
        "device_uuid": "device-uuid-phone-a"
    })
    assert response.status_code == 200
    res_data = response.get_json()
    token_a = res_data["token"]
    assert res_data["device_uuid"] == "device-uuid-phone-a"
    assert len(token_a) == 64

    # 2. Make authenticated request using Device A token
    headers_a = {"Authorization": f"Bearer {token_a}"}
    response = client.get("/api/v1/panchanga", query_string=begaluru_query_str(bengaluru_query), headers=headers_a)
    assert response.status_code == 200

    # 3. Login on Device B (Multi-device support)
    response_b = client.post("/api/v1/auth/login", json={
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


def test_same_device_relogin_and_logout(client, clean_users_store, bengaluru_query):
    # 1. Login on Phone A -> gets token_a1
    res1 = client.post("/api/v1/auth/login", json={"device_uuid": "phone-a"})
    assert res1.status_code == 200
    token_a1 = res1.get_json()["token"]

    # 2. Login AGAIN on Phone A -> gets token_a2 (replaces old token for phone-a)
    res2 = client.post("/api/v1/auth/login", json={"device_uuid": "phone-a"})
    assert res2.status_code == 200
    token_a2 = res2.get_json()["token"]
    assert token_a2 != token_a1

    # token_a2 works
    headers_a2 = {"Authorization": f"Bearer {token_a2}"}
    assert client.get("/api/v1/panchanga", query_string=begaluru_query_str(bengaluru_query), headers=headers_a2).status_code == 200

    # Old token_a1 on same device was replaced and is no longer valid
    headers_a1 = {"Authorization": f"Bearer {token_a1}"}
    assert client.get("/api/v1/panchanga", query_string=begaluru_query_str(bengaluru_query), headers=headers_a1).status_code == 401

    # 3. Explicit logout from token_a2 -> deletes device entry from users.json
    logout_res = client.post("/api/v1/auth/logout", headers=headers_a2)
    assert logout_res.status_code == 200
    assert client.get("/api/v1/panchanga", query_string=begaluru_query_str(bengaluru_query), headers=headers_a2).status_code == 401

    # Verify device record is deleted from users.json store
    assert get_active_users_count() == 0


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


def test_cli_list_users(app, client, clean_users_store):
    runner = app.test_cli_runner()
    # Before login
    res_before = runner.invoke(args=["list-users"])
    assert "Total active users: 0" in res_before.output

    # Login two devices
    client.post("/api/v1/auth/login", json={"device_uuid": "device-1"})
    client.post("/api/v1/auth/login", json={"device_uuid": "device-2"})

    res_after = runner.invoke(args=["list-users"])
    assert "Total active users: 2" in res_after.output


def begaluru_query_str(query):
    q = query.copy()
    if "datetime" in q:
        del q["datetime"]
    q["date"] = "2026-07-20"
    return q
