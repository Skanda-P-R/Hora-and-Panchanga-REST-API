from __future__ import annotations

import json
import pytest

from hora_server.extensions import cache


@pytest.fixture()
def clean_registry(app):
    """Fixture to reset the location registry before each test."""
    registry = app.extensions["location_registry"]
    with registry.lock:
        registry._save({"saved_locations": {}, "favorite_cities": {}})
    cache.clear()
    yield registry


def test_date_alias_panchanga(client, bengaluru_query):
    # Remove datetime and add date instead
    query = bengaluru_query.copy()
    del query["datetime"]
    query["date"] = "2026-07-20"

    response = client.get("/api/v1/panchanga", query_string=query)
    assert response.status_code == 200
    data = response.get_json()
    assert data["date"] == "2026-07-20"
    assert data["local_date"] == "2026-07-20"
    assert "panchanga" in data


def test_date_and_time_panchanga(client, bengaluru_query):
    # Remove datetime and add date + time separately
    query = bengaluru_query.copy()
    del query["datetime"]
    query["date"] = "2026-07-20"
    query["time"] = "13:46:00"

    response = client.get("/api/v1/panchanga", query_string=query)
    assert response.status_code == 200
    data = response.get_json()
    assert data["local_date"] == "2026-07-20"
    assert "13:46:00" in data["datetime"]
    assert "panchanga" in data


def test_birth_chart_endpoints(client, bengaluru_query):
    query = bengaluru_query.copy()
    query["name"] = "Rama"

    # Test JSON endpoint
    response = client.get("/api/v1/kundali/birth", query_string=query)
    assert response.status_code == 200
    data = response.get_json()
    assert data["name"] == "Rama"
    assert "lagna" in data
    assert "houses" in data
    assert "planets" in data

    # Test PNG rendering endpoint
    response = client.get("/api/v1/kundali/birth/chart", query_string=query)
    assert response.status_code == 200
    assert response.content_type == "image/png"
    assert len(response.data) > 0

    # Test SVG rendering endpoint
    response = client.get("/api/v1/kundali/birth/svg", query_string=query)
    assert response.status_code == 200
    assert response.content_type.startswith("image/svg+xml")
    assert b"<svg" in response.data


def test_locations_crud_and_resolution(client, clean_registry):
    # 1. Verify initially empty
    response = client.get("/api/v1/locations")
    assert response.status_code == 200
    assert response.get_json() == {}

    # 2. Add saved location
    loc_payload = {
        "name": "Home",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "timezone": "Asia/Kolkata",
        "description": "Sweet Home"
    }
    response = client.post("/api/v1/locations", json=loc_payload)
    assert response.status_code == 201
    assert response.get_json() == {"status": "saved", "name": "Home"}

    # 3. Retrieve locations and check
    response = client.get("/api/v1/locations")
    assert response.status_code == 200
    data = response.get_json()
    assert "Home" in data
    assert data["Home"]["latitude"] == 12.9716
    assert data["Home"]["timezone"] == "Asia/Kolkata"

    # 4. Resolve coordinates in calculation endpoint
    response = client.get(
        "/api/v1/panchanga",
        query_string={"location": "Home", "date": "2026-07-20"}
    )
    assert response.status_code == 200
    res_data = response.get_json()
    assert res_data["date"] == "2026-07-20"
    assert res_data["coordinates"]["latitude"] == 12.9716

    # 5. Delete saved location
    response = client.delete("/api/v1/locations/Home")
    assert response.status_code == 200
    assert response.get_json() == {"status": "deleted", "name": "Home"}
    cache.clear()  # Clear cache after mutation to prevent hitting cached 200 result

    # 6. Retrieve again and verify empty
    response = client.get("/api/v1/locations")
    assert response.status_code == 200
    assert response.get_json() == {}

    # 7. Check location not found error in calculation
    response = client.get(
        "/api/v1/panchanga",
        query_string={"location": "Home", "date": "2026-07-20"}
    )
    assert response.status_code == 404
    err_data = response.get_json()
    assert err_data["error"]["code"] == "location_not_found"


def test_favorites_crud_and_resolution(client, clean_registry):
    # 1. Verify initially empty
    response = client.get("/api/v1/favorites")
    assert response.status_code == 200
    assert response.get_json() == {}

    # 2. Add favorite city
    city_payload = {
        "name": "Bengaluru",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "timezone": "Asia/Kolkata",
        "country": "India"
    }
    response = client.post("/api/v1/favorites", json=city_payload)
    assert response.status_code == 201
    assert response.get_json() == {"status": "saved", "name": "Bengaluru"}

    # 3. Retrieve favorites and check
    response = client.get("/api/v1/favorites")
    assert response.status_code == 200
    data = response.get_json()
    assert "Bengaluru" in data
    assert data["Bengaluru"]["latitude"] == 12.9716

    # 4. Resolve coordinates in calculation endpoint
    response = client.get(
        "/api/v1/panchanga",
        query_string={"location": "Bengaluru", "date": "2026-07-20"}
    )
    assert response.status_code == 200
    res_data = response.get_json()
    assert res_data["date"] == "2026-07-20"
    assert res_data["coordinates"]["latitude"] == 12.9716

    # 5. Delete favorite
    response = client.delete("/api/v1/favorites/Bengaluru")
    assert response.status_code == 200
    assert response.get_json() == {"status": "deleted", "name": "Bengaluru"}
    cache.clear()  # Clear cache after mutation to prevent hitting cached 200 result

    # 6. Retrieve again and verify empty
    response = client.get("/api/v1/favorites")
    assert response.status_code == 200
    assert response.get_json() == {}
