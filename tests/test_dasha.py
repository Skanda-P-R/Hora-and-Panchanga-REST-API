from __future__ import annotations

from datetime import datetime, UTC
from zoneinfo import ZoneInfo
import pytest

from hora_server.astrology.dasha import calculate_dasha, NAKSHATRAS, DASHA_LORDS, DASHA_YEARS


def test_dasha_calculation_revati():
    start_time = datetime(2026, 7, 8, 12, 0, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    # Revati spans from 346.6666... to 360.0
    moon_details, balance, timeline, active = calculate_dasha(
        moon_longitude=357.7080,
        start_time=start_time,
        year_days=365.25,
        depth=3
    )

    assert moon_details.nakshatra == "Revati"
    assert moon_details.nakshatra_number == 27
    assert moon_details.nakshatra_lord == "Mercury"
    assert moon_details.rasi == "Pisces"
    assert moon_details.rasi_number == 12

    assert balance.lord == "Mercury"
    assert balance.total_years == 17.0
    # Expected elapsed fraction: (357.7080 - 346.6666...) / 13.3333... = 11.04133... / 13.3333... = 0.8281
    assert balance.elapsed_fraction == pytest.approx(0.8281, abs=0.0001)
    assert balance.remaining_fraction == pytest.approx(0.1719, abs=0.0001)

    assert len(timeline) == 10
    # First Mahadasha is Mercury
    assert timeline[0].lord == "Mercury"
    # Durations should sum to 120 years theoretically across 9 full cycles,
    # but since the first is partial and we have 10 entries (Mercury to Mercury),
    # let's verify individual durations.
    assert timeline[0].duration_years == 17.0
    assert timeline[1].lord == "Ketu"
    assert timeline[1].duration_years == 7.0

    # Contiguity check
    for i in range(9):
        assert timeline[i].end == timeline[i+1].start

    # Active dasha checking
    assert active.mahadasha == "Mercury"


def test_dasha_calculation_boundaries():
    start_time = datetime(2026, 7, 8, 12, 0, 0, tzinfo=UTC)
    
    # 0.0 degrees is start of Ashwini (Ketu)
    moon, bal, timeline, active = calculate_dasha(0.0, start_time)
    assert moon.nakshatra == "Ashwini"
    assert moon.nakshatra_lord == "Ketu"
    assert bal.elapsed_fraction == 0.0
    assert bal.remaining_fraction == 1.0

    # 13.33333333 is start of Bharani (Venus)
    moon, bal, timeline, active = calculate_dasha(13.3334, start_time)
    assert moon.nakshatra == "Bharani"
    assert moon.nakshatra_lord == "Venus"


def test_api_get_dasha_default(client, bengaluru_query):
    response = client.get("/api/v1/dasha", query_string=bengaluru_query)
    assert response.status_code == 200
    data = response.get_json()

    # Schema checks
    assert set(data) == {
        "date",
        "datetime",
        "timezone",
        "ayanamsa",
        "year_type",
        "moon",
        "dasha_balance",
        "active_dasha",
        "timeline"
    }

    assert data["date"] == "2026-07-08"
    assert data["timezone"] == "Asia/Kolkata"
    assert data["ayanamsa"] == "Lahiri"
    assert data["year_type"] == "365.25"

    assert data["moon"]["nakshatra"] == "Revati"
    assert data["moon"]["nakshatra_lord"] == "Mercury"

    assert data["dasha_balance"]["lord"] == "Mercury"
    assert data["active_dasha"]["mahadasha"] == "Mercury"
    assert len(data["timeline"]) == 10

    # Default depth = 2, meaning sub_periods (Antardashas) are present
    assert len(data["timeline"][0]["sub_periods"]) == 9
    assert data["timeline"][0]["sub_periods"][0]["lord"] == "Mercury"
    # L3 sub_periods should be empty
    assert len(data["timeline"][0]["sub_periods"][0]["sub_periods"]) == 0


def test_api_get_dasha_depths(client, bengaluru_query):
    # Depth 1: Mahadashas only
    q1 = bengaluru_query.copy()
    q1["depth"] = "1"
    res1 = client.get("/api/v1/dasha", query_string=q1)
    assert res1.status_code == 200
    data1 = res1.get_json()
    assert len(data1["timeline"][0]["sub_periods"]) == 0
    assert "pratyantardasha" not in data1["active_dasha"]

    # Depth 3: Mahadasha + Antardasha + Pratyantardasha
    q3 = bengaluru_query.copy()
    q3["depth"] = "3"
    res3 = client.get("/api/v1/dasha", query_string=q3)
    assert res3.status_code == 200
    data3 = res3.get_json()
    assert len(data3["timeline"][0]["sub_periods"]) == 9
    assert len(data3["timeline"][0]["sub_periods"][0]["sub_periods"]) == 9
    assert "pratyantardasha" in data3["active_dasha"]


def test_api_get_dasha_savana_year(client, bengaluru_query):
    q = bengaluru_query.copy()
    q["year_type"] = "360"
    response = client.get("/api/v1/dasha", query_string=q)
    assert response.status_code == 200
    data = response.get_json()
    assert data["year_type"] == "360.0"


def test_api_get_dasha_localization(client, bengaluru_query):
    q = bengaluru_query.copy()
    q["lang"] = "kan"
    response = client.get("/api/v1/dasha", query_string=q)
    assert response.status_code == 200
    data = response.get_json()

    # Rasi name "Pisces" -> "ಮೀನ"
    assert data["moon"]["rasi"] == "ಮೀನ"
    # Nakshatra name "Revati" -> "ರೇವತಿ"
    assert data["moon"]["nakshatra"] == "ರೇವತಿ"
    # Lord name "Mercury" -> "ಬುಧ"
    assert data["moon"]["nakshatra_lord"] == "ಬುಧ"
    assert data["dasha_balance"]["lord"] == "ಬುಧ"
    assert data["active_dasha"]["mahadasha"] == "ಬುಧ"
    assert data["timeline"][0]["lord"] == "ಬುಧ"
