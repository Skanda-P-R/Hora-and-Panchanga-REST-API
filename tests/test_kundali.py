from __future__ import annotations

import struct
import sys
import types
import zlib

import pytest

from hora_server.render.chart_symbols import KANNADA_TITLE, degree_minute_text
from hora_server.render.chart_symbols import localized_symbol


def _planet(data, name):
    return next(planet for planet in data["planets"] if planet["planet"] == name)


def _house(data, number):
    return next(house for house in data["houses"] if house["house"] == number)


def _blank_png(width=512, height=512):
    rows = bytearray()
    row = bytes([255] * width * 3)
    for _ in range(height):
        rows.append(0)
        rows.extend(row)
    payload = zlib.compress(bytes(rows))

    def chunk(kind, data):
        checksum = zlib.crc32(kind + data) & 0xFFFFFFFF
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", checksum)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", payload)
        + chunk(b"IEND", b"")
    )



def test_degree_minute_text_includes_minute_mark():
    assert degree_minute_text(1.3567) == "1\N{DEGREE SIGN}21'"


def test_kundali_reference_schema_and_positions(client, bengaluru_query):
    response = client.get("/api/v1/kundali", query_string=bengaluru_query)

    assert response.status_code == 200
    data = response.get_json()
    assert set(data) == {
        "date",
        "datetime",
        "timezone",
        "lagna",
        "houses",
        "planets",
        "ayanamsa",
    }
    assert data["date"] == "2026-07-08"
    assert data["timezone"] == "Asia/Kolkata"
    assert data["ayanamsa"] == "Lahiri"

    assert data["lagna"]["rasi"] == "Virgo"
    assert data["lagna"]["number"] == 6
    assert data["lagna"]["longitude"] == pytest.approx(166.9770, abs=0.0001)
    assert data["lagna"]["degree_in_rasi"] == pytest.approx(
        16.9770, abs=0.0001
    )

    assert len(data["houses"]) == 12
    assert len(data["planets"]) == 9
    assert [planet["planet"] for planet in data["planets"]] == [
        "Sun",
        "Moon",
        "Mars",
        "Mercury",
        "Jupiter",
        "Venus",
        "Saturn",
        "Rahu",
        "Ketu",
    ]

    expected = {
        "Sun": ("Gemini", 10, 81.9045, False),
        "Moon": ("Pisces", 7, 357.7080, False),
        "Mars": ("Taurus", 9, 42.4714, False),
        "Mercury": ("Gemini", 10, 89.4395, True),
        "Jupiter": ("Cancer", 11, 97.5019, False),
        "Venus": ("Leo", 12, 124.1491, False),
        "Saturn": ("Pisces", 7, 350.2275, False),
        "Rahu": ("Aquarius", 6, 307.9721, True),
        "Ketu": ("Leo", 12, 127.9721, True),
    }
    for name, (rasi, house, longitude, retrograde) in expected.items():
        planet = _planet(data, name)
        assert planet["rasi"] == rasi
        assert planet["house"] == house
        assert planet["longitude"] == pytest.approx(longitude, abs=0.0001)
        assert planet["retrograde"] is retrograde

    assert _house(data, 6)["planets"] == ["Rahu"]
    assert _house(data, 7)["planets"] == ["Moon", "Saturn"]
    assert _house(data, 10)["planets"] == ["Sun", "Mercury"]
    assert _house(data, 12)["planets"] == ["Venus", "Ketu"]


def test_rahu_and_ketu_are_opposite_points(client, bengaluru_query):
    data = client.get("/api/v1/kundali", query_string=bengaluru_query).get_json()
    rahu = _planet(data, "Rahu")
    ketu = _planet(data, "Ketu")

    assert (ketu["longitude"] - rahu["longitude"]) % 360 == pytest.approx(
        180, abs=0.0001
    )
    assert ketu["degree_in_rasi"] == pytest.approx(
        rahu["degree_in_rasi"], abs=0.0001
    )


def test_kundali_chart_png_and_svg_render(client, bengaluru_query):
    png = client.get("/api/v1/kundali/chart", query_string=bengaluru_query)
    assert png.status_code == 200
    assert png.content_type == "image/png"
    assert png.data.startswith(b"\x89PNG\r\n\x1a\n")
    width, height = struct.unpack(">II", png.data[16:24])
    assert (width, height) == (512, 512)

    svg = client.get("/api/v1/kundali/svg", query_string=bengaluru_query)
    assert svg.status_code == 200
    assert svg.content_type.startswith("image/svg+xml")
    assert b"<svg" in svg.data
    assert b"AS" in svg.data
    assert b"Ra(R)" in svg.data
    assert b"Transit Kundali" in svg.data
    assert b"2026-07-08" in svg.data
    assert b"12:00:00 +0530" in svg.data
    assert b"Lat 12.971600, Lon 77.594600" in svg.data


def test_kundali_chart_supports_kannada_language(
    client, bengaluru_query
):
    query = {**bengaluru_query, "lang": "kan"}
    svg = client.get("/api/v1/kundali/svg", query_string=query)
    assert svg.status_code == 200
    text = svg.data.decode()
    assert "ಗೋಚಾರ ಕುಂಡಲಿ" in text
    assert "ಲಗ್ನ" in text
    assert "ರಾಹು(R)" in text
    assert "ಸೂರ್ಯ" in text
    assert "Transit Kundali" not in text
    assert "AS" not in text

    png = client.get("/api/v1/kundali/chart", query_string=query)
    assert png.status_code == 200
    assert png.content_type == "image/png"
    assert png.data.startswith(b"\x89PNG\r\n\x1a\n")


def test_invalid_chart_language_has_stable_error(client, bengaluru_query):
    response = client.get(
        "/api/v1/kundali/svg",
        query_string={**bengaluru_query, "lang": "sa"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_parameter"
    assert response.get_json()["error"]["details"]["parameter"] == "lang"


def test_symbol_localization_map_matches_kannada_contract():
    assert localized_symbol("Su", "kan") == "ಸೂರ್ಯ"
    assert localized_symbol("Mo", "kan") == "ಚಂದ್ರ"
    assert localized_symbol("Ma", "kan") == "ಕುಜ"
    assert localized_symbol("Me", "kan") == "ಬುಧ"
    assert localized_symbol("Ju", "kan") == "ಗುರು"
    assert localized_symbol("Ve", "kan") == "ಶುಕ್ರ"
    assert localized_symbol("Sa", "kan") == "ಶನಿ"
    assert localized_symbol("Ra", "kan") == "ರಾಹು"
    assert localized_symbol("Ke", "kan") == "ಕೇತು"
    assert localized_symbol("AS", "kan") == "ಲಗ್ನ"


def test_kundali_chart_center_is_a_single_information_panel(
    client, bengaluru_query
):
    png = client.get("/api/v1/kundali/chart", query_string=bengaluru_query)
    assert png.status_code == 200

    svg = client.get("/api/v1/kundali/svg", query_string=bengaluru_query)
    text = svg.data.decode()
    assert 'x1="256" y1="128" x2="256" y2="384"' not in text
    assert 'x1="128" y1="256" x2="384" y2="256"' not in text


def test_all_declared_chart_styles_are_accepted(
    client, bengaluru_query
):
    for style in ("south", "north", "east"):
        response = client.get(
            "/api/v1/kundali/chart",
            query_string={**bengaluru_query, "chart_style": style},
        )
        assert response.status_code == 200
        assert response.content_type == "image/png"


def test_invalid_chart_style_has_stable_error(client, bengaluru_query):
    response = client.get(
        "/api/v1/kundali/chart",
        query_string={**bengaluru_query, "chart_style": "west"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_parameter"
    assert response.get_json()["error"]["details"]["parameter"] == "chart_style"


def test_kundali_is_not_added_to_existing_aggregate(client, bengaluru_query):
    data = client.get("/api/v1/all", query_string=bengaluru_query).get_json()

    assert "kundali" not in data
    assert "lagna" not in data
    assert "houses" not in data
