from __future__ import annotations

from pathlib import Path

import pytest

from hora_server import create_app


@pytest.fixture(scope="session")
def app():
    project_root = Path(__file__).resolve().parents[1]
    return create_app(
        {
            "TESTING": True,
            "EPHEMERIS_PATH": str(project_root / "hora_server" / "ephe"),
            "STRICT_SWISS_EPHEMERIS": True,
        }
    )


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(scope="session")
def bengaluru_query():
    return {
        "lat": "12.9716",
        "lon": "77.5946",
        "datetime": "2026-07-08T12:00:00+05:30",
        "timezone": "Asia/Kolkata",
        "ayanamsa": "lahiri",
    }
