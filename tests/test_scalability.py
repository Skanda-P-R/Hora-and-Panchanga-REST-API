from __future__ import annotations

import time
from pathlib import Path

import cachelib.simple
import pytest

from hora_server import create_app
from hora_server.extensions import cache, limiter


def _app():
    project_root = Path(__file__).resolve().parents[1]
    return create_app(
        {
            "TESTING": True,
            "EPHEMERIS_PATH": str(project_root / "hora_server" / "ephe"),
            "STRICT_SWISS_EPHEMERIS": True,
        }
    )


@pytest.fixture()
def isolated_app():
    app = _app()
    cache.clear()
    limiter.reset()
    yield app
    cache.clear()
    limiter.reset()


@pytest.fixture()
def isolated_client(isolated_app):
    return isolated_app.test_client()


def _query(**overrides):
    query = {
        "lat": "12.9716",
        "lon": "77.5946",
        "datetime": "2026-07-08T12:00:00+05:30",
        "timezone": "Asia/Kolkata",
        "ayanamsa": "lahiri",
    }
    query.update(overrides)
    return query


def test_all_endpoint_cache_hit_avoids_repeated_service_call(
    isolated_app, isolated_client
):
    calls = {"count": 0}

    def fake_all(context):
        calls["count"] += 1
        return {"value": calls["count"], "lat": context.latitude}

    isolated_app.extensions["panchanga_service"].all = fake_all

    first = isolated_client.get("/api/v1/all", query_string=_query())
    second = isolated_client.get("/api/v1/all", query_string=_query())

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.get_json() == {"value": 1, "lat": 12.9716}
    assert second.get_json() == first.get_json()
    assert calls["count"] == 1


def test_newly_cached_panchanga_endpoint_avoids_repeated_service_call(
    isolated_app, isolated_client
):
    calls = {"count": 0}

    def fake_panchanga(context):
        calls["count"] += 1
        return {"value": calls["count"], "timezone": context.timezone.key}

    isolated_app.extensions["panchanga_service"].panchanga = fake_panchanga

    first = isolated_client.get("/api/v1/panchanga", query_string=_query())
    second = isolated_client.get("/api/v1/panchanga", query_string=_query())

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.get_json() == {"value": 1, "timezone": "Asia/Kolkata"}
    assert second.get_json() == first.get_json()
    assert calls["count"] == 1


def test_cache_backend_expires_entries(monkeypatch, isolated_app):
    now = {"value": time.time()}
    monkeypatch.setattr(cachelib.simple, "time", lambda: now["value"])

    cache.set("short-lived", "cached", timeout=1)
    assert cache.get("short-lived") == "cached"

    now["value"] += 2

    assert cache.get("short-lived") is None


def test_query_string_cache_separation(isolated_app, isolated_client):
    calls = {"count": 0}

    def fake_kundali(context):
        calls["count"] += 1
        return {"value": calls["count"], "datetime": context.instant.isoformat()}

    isolated_app.extensions["panchanga_service"].kundali = fake_kundali

    first = isolated_client.get("/api/v1/kundali", query_string=_query())
    second = isolated_client.get(
        "/api/v1/kundali",
        query_string=_query(datetime="2026-07-08T13:00:00+05:30"),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.get_json()["value"] == 1
    assert second.get_json()["value"] == 2
    assert calls["count"] == 2


def test_coordinates_are_normalized_before_service_calculation(
    isolated_app, isolated_client
):
    seen = {}

    def fake_all(context):
        seen["latitude"] = context.latitude
        seen["longitude"] = context.longitude
        return {"ok": True}

    isolated_app.extensions["panchanga_service"].all = fake_all

    response = isolated_client.get(
        "/api/v1/all",
        query_string=_query(lat="12.97164", lon="77.59465"),
    )

    assert response.status_code == 200
    assert seen == {"latitude": 12.9716, "longitude": 77.5947}


@pytest.mark.parametrize(
    ("endpoint", "service_method"),
    (
        ("/api/v1/hora", "hora"),
        ("/api/v1/planetary-hours", "planetary_hours"),
        ("/api/v1/panchanga", "panchanga"),
        ("/api/v1/day", "day"),
        ("/api/v1/calendar", "calendar"),
        ("/api/v1/muhurta", "muhurta"),
        ("/api/v1/rahu", "rahu"),
        ("/api/v1/all", "all"),
        ("/api/v1/kundali", "kundali"),
    ),
)
def test_json_api_cache_control_header_is_returned(
    isolated_app, isolated_client, endpoint, service_method
):
    setattr(
        isolated_app.extensions["panchanga_service"],
        service_method,
        lambda context: {"ok": True},
    )

    response = isolated_client.get(endpoint, query_string=_query())

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "public, max-age=60"


@pytest.mark.parametrize("endpoint", ("/api/v1/kundali/chart", "/api/v1/kundali/svg"))
def test_rendered_kundali_cache_control_header_is_returned(
    isolated_client, endpoint
):
    response = isolated_client.get(endpoint, query_string=_query())

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "public, max-age=60"


def test_rate_limit_returns_429_and_can_reset(isolated_app, isolated_client):
    isolated_app.extensions["panchanga_service"].all = lambda context: {"ok": True}

    for _ in range(60):
        response = isolated_client.get("/api/v1/all", query_string=_query())
        assert response.status_code == 200

    limited = isolated_client.get("/api/v1/all", query_string=_query())
    assert limited.status_code == 429
    assert limited.get_json()["error"]["code"] == "too_many_requests"

    limiter.reset()
    reset = isolated_client.get("/api/v1/all", query_string=_query())
    assert reset.status_code == 200
