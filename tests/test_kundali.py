from __future__ import annotations

import struct
import zlib

import pytest

from hora_server.render.chart_symbols import SimpleCanvas, degree_minute_text


def _planet(data, name):
    return next(planet for planet in data["planets"] if planet["planet"] == name)


def _house(data, number):
    return next(house for house in data["houses"] if house["house"] == number)


def _png_pixel(data, x, y):
    offset = 8
    idat = bytearray()
    width, height = struct.unpack(">II", data[16:24])
    while offset < len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        if kind == b"IDAT":
            idat.extend(payload)
        offset += 12 + length

    rows = zlib.decompress(bytes(idat))
    stride = width * 3 + 1
    row = rows[y * stride : (y + 1) * stride]
    assert row[0] == 0
    start = 1 + x * 3
    assert height == 512
    return tuple(row[start : start + 3])


def test_degree_minute_text_includes_minute_mark():
    assert degree_minute_text(1.3567) == "1\N{DEGREE SIGN}21'"


def test_png_font_draws_minute_mark():
    canvas = SimpleCanvas(width=24, height=24)
    canvas.text("'", 2, 2, scale=2)

    assert any(value != 255 for value in canvas.pixels)


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


def test_kundali_chart_center_is_a_single_information_panel(
    client, bengaluru_query
):
    png = client.get("/api/v1/kundali/chart", query_string=bengaluru_query)
    assert _png_pixel(png.data, 256, 150) == (255, 255, 255)
    assert _png_pixel(png.data, 150, 256) == (255, 255, 255)

    svg = client.get("/api/v1/kundali/svg", query_string=bengaluru_query)
    text = svg.data.decode()
    assert 'x1="256" y1="128" x2="256" y2="384"' not in text
    assert 'x1="128" y1="256" x2="384" y2="256"' not in text


def test_all_declared_chart_styles_are_accepted(client, bengaluru_query):
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
