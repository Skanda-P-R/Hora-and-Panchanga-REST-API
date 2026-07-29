from __future__ import annotations

from datetime import datetime, timedelta


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_all_endpoints_are_available(client, bengaluru_query):
    for endpoint in (
        "hora",
        "panchanga",
        "day",
        "planetary-hours",
        "calendar",
        "muhurta",
        "rahu",
        "all",
    ):
        response = client.get(f"/api/v1/{endpoint}", query_string=bengaluru_query)
        assert response.status_code == 200, (endpoint, response.get_json())
        assert response.is_json


def test_bengaluru_reference_case(client, bengaluru_query):
    """Cross-checked against multiple published Bengaluru Panchangas.

    For 2026-07-08, Ashtami ends around 12:22-12:24 IST and Revati around
    16:00-16:01 IST. Sources round differently; the Swiss result is retained
    at second precision.
    """
    response = client.get("/api/v1/all", query_string=bengaluru_query)
    assert response.status_code == 200
    data = response.get_json()

    assert data["panchanga"]["tithi"] == "Krishna Ashtami"
    assert data["panchanga"]["nakshatra"] == "Revati"
    assert data["panchanga"]["vara"] == "Wednesday"
    assert data["panchanga"]["karana"] == "Kaulava"
    assert data["panchanga"]["yoga"] == "Atiganda"
    assert data["panchanga"]["samvatsara"] == "Parabhava"
    assert data["panchanga"]["ayana"] == "Uttarayana"
    assert data["panchanga"]["rutu"] == "Grishma"
    assert data["panchanga"]["masa"] == "Jyeshtha"
    assert data["panchanga"]["paksha"] == "Krishna"
    assert data["moon"]["rasi"] == "Meena"
    assert data["moon"]["pada"] == 4
    assert data["sun"]["rasi"] == "Mithuna"
    assert data["meta"]["ephemeris_backend"] == "swiss"
    assert data["meta"]["solar_event_swiss_flag"] == "BIT_HINDU_RISING"

    sunrise = datetime.fromisoformat(data["sunrise_at"])
    sunset = datetime.fromisoformat(data["sunset_at"])
    assert abs((sunrise - datetime.fromisoformat("2026-07-08T06:02:45.945+05:30")).total_seconds()) < 2
    assert abs((sunset - datetime.fromisoformat("2026-07-08T18:46:33.840+05:30")).total_seconds()) < 2

    tithi_end = datetime.fromisoformat(
        data["panchanga_details"]["tithi"]["ends_at"]
    )
    nakshatra_end = datetime.fromisoformat(
        data["panchanga_details"]["nakshatra"]["ends_at"]
    )
    assert (tithi_end.hour, tithi_end.minute) in {(12, 22), (12, 23), (12, 24)}
    assert (nakshatra_end.hour, nakshatra_end.minute) in {(15, 59), (16, 0), (16, 1)}


def test_all_agrees_with_individual_endpoints(client, bengaluru_query):
    aggregate = client.get(
        "/api/v1/all", query_string=bengaluru_query
    ).get_json()
    hora = client.get("/api/v1/hora", query_string=bengaluru_query).get_json()
    panchanga = client.get(
        "/api/v1/panchanga", query_string=bengaluru_query
    ).get_json()
    muhurta = client.get(
        "/api/v1/muhurta", query_string=bengaluru_query
    ).get_json()
    rahu = client.get("/api/v1/rahu", query_string=bengaluru_query).get_json()

    assert aggregate["hora"] == hora["hora"]
    assert aggregate["panchanga"] == panchanga["panchanga"]
    assert aggregate["panchanga_details"] == panchanga["panchanga_details"]
    assert aggregate["muhurta"] == muhurta["muhurta"]
    assert aggregate["rahu_kalam"] == rahu["rahu_kalam"]


def test_real_day_and_night_horas_tile_separate_unequal_spans(
    client, bengaluru_query
):
    data = client.get(
        "/api/v1/planetary-hours", query_string=bengaluru_query
    ).get_json()
    hours = data["planetary_hours"]
    assert len(hours) == 24
    assert all(left["end"] == right["start"] for left, right in zip(hours, hours[1:]))
    assert hours[0]["start"] == data["sunrise_at"]
    assert hours[11]["end"] == data["sunset_at"]
    assert hours[-1]["end"] == data["next_sunrise_at"]
    assert data["day_hora_seconds"] != data["night_hora_seconds"]


def test_hora_endpoint_includes_day_and_night_hora(client, bengaluru_query):
    data = client.get("/api/v1/hora", query_string=bengaluru_query).get_json()
    assert "day_hora" in data
    assert "night_hora" in data
    assert len(data["day_hora"]) == 12
    assert len(data["night_hora"]) == 12

    expected_keys = {"planet", "symbol", "number", "starts", "ends", "starts_at", "ends_at"}

    first_day = data["day_hora"][0]
    assert expected_keys.issubset(first_day.keys())
    assert first_day["number"] == 1

    first_night = data["night_hora"][0]
    assert expected_keys.issubset(first_night.keys())
    assert first_night["number"] == 1



def test_exact_sunrise_and_sunset_use_half_open_hora_boundaries(
    client, bengaluru_query
):
    day = client.get("/api/v1/day", query_string=bengaluru_query).get_json()
    sunrise = datetime.fromisoformat(day["sunrise_at"])
    sunset = datetime.fromisoformat(day["sunset_at"])

    def hora_at(instant):
        query = dict(bengaluru_query)
        query["datetime"] = instant.isoformat()
        return client.get("/api/v1/hora", query_string=query).get_json()["hora"]

    assert hora_at(sunrise)["period_number"] == 1
    assert hora_at(sunrise)["period"] == "day"
    assert hora_at(sunrise - timedelta(microseconds=1))["period_number"] == 12
    assert hora_at(sunrise - timedelta(microseconds=1))["period"] == "night"
    assert hora_at(sunset)["period_number"] == 1
    assert hora_at(sunset)["period"] == "night"
    assert hora_at(sunset - timedelta(microseconds=1))["period_number"] == 12
    assert hora_at(sunset - timedelta(microseconds=1))["period"] == "day"


def test_timezone_is_inferred_offline(client, bengaluru_query):
    query = dict(bengaluru_query)
    query.pop("timezone")
    data = client.get("/api/v1/day", query_string=query).get_json()
    assert data["timezone"] == "Asia/Kolkata"


def test_pre_sunrise_uses_previous_vedic_weekday(client):
    query = {
        "lat": "12.9716",
        "lon": "77.5946",
        "timezone": "Asia/Kolkata",
        "datetime": "2026-07-08T04:00:00+05:30",
    }
    data = client.get("/api/v1/all", query_string=query).get_json()
    assert data["date"] == "2026-07-07"
    assert data["local_date"] == "2026-07-08"
    assert data["vedic_day_date"] == "2026-07-07"
    assert data["panchanga"]["vara"] == "Tuesday"
    assert data["hora"]["period"] == "night"


def test_missing_and_invalid_parameters_have_stable_errors(client):
    missing = client.get("/api/v1/all?lon=77")
    assert missing.status_code == 400
    assert missing.get_json()["error"]["code"] == "missing_parameter"

    invalid = client.get("/api/v1/all?lat=91&lon=77")
    assert invalid.status_code == 400
    assert invalid.get_json()["error"]["code"] == "invalid_parameter"

    timezone = client.get(
        "/api/v1/all?lat=12&lon=77&timezone=Not/AZone"
    )
    assert timezone.status_code == 400
    assert timezone.get_json()["error"]["code"] == "invalid_timezone"


def test_out_of_bundled_ephemeris_range_is_rejected(client):
    response = client.get(
        "/api/v1/all",
        query_string={
            "lat": "12",
            "lon": "77",
            "timezone": "Asia/Kolkata",
            "datetime": "1799-12-31T12:00:00+05:30",
        },
    )
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "datetime_out_of_range"


def test_timezone_overflow_returns_422_not_500(client):
    response = client.get(
        "/api/v1/day",
        query_string={
            "lat": "12",
            "lon": "77",
            "timezone": "Asia/Kolkata",
            "datetime": "9999-12-31T23:59:59-12:00",
        },
    )
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "datetime_out_of_range"


def test_public_ephemeris_range_edges_stay_on_swiss_backend(client):
    for timestamp in (
        "1800-01-01T12:00:00+00:00",
        "2399-12-31T12:00:00+00:00",
    ):
        response = client.get(
            "/api/v1/panchanga",
            query_string={
                "lat": "0",
                "lon": "0",
                "timezone": "UTC",
                "datetime": timestamp,
            },
        )
        assert response.status_code == 200, response.get_json()
        assert response.get_json()["meta"]["ephemeris_backend"] == "swiss"


def test_non_panchanga_endpoints_do_not_solve_limb_transitions(
    app, client, bengaluru_query, monkeypatch
):
    import hora_server.service as service_module

    def fail_if_called(*args, **kwargs):
        raise AssertionError("calculate_panchanga should not be called")

    monkeypatch.setattr(service_module, "calculate_panchanga", fail_if_called)
    for endpoint in ("hora", "planetary-hours", "day", "muhurta", "rahu"):
        response = client.get(f"/api/v1/{endpoint}", query_string=bengaluru_query)
        assert response.status_code == 200, endpoint


def test_calendar_is_a_chronological_local_day_timeline(client, bengaluru_query):
    data = client.get("/api/v1/calendar", query_string=bengaluru_query).get_json()
    event_times = [datetime.fromisoformat(event["at"]) for event in data["events"]]
    assert event_times == sorted(event_times)
    assert {event["type"] for event in data["events"]} >= {
        "sunrise",
        "sunset",
        "tithi_transition",
        "nakshatra_transition",
        "karana_transition",
    }


def test_polar_day_reports_dependent_calculation_unavailable(client):
    response = client.get(
        "/api/v1/day",
        query_string={
            "lat": "78.2232",
            "lon": "15.6469",
            "timezone": "Arctic/Longyearbyen",
            "datetime": "2026-06-21T12:00:00+02:00",
        },
    )
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "solar_event_unavailable"


def test_representative_request_is_fully_offline(
    client, bengaluru_query, monkeypatch
):
    import socket

    def reject_network(*args, **kwargs):
        raise AssertionError("network access is forbidden during calculations")

    monkeypatch.setattr(socket, "create_connection", reject_network)
    response = client.get("/api/v1/all", query_string=bengaluru_query)
    assert response.status_code == 200


def test_kannada_language_localization(client, bengaluru_query):
    query = bengaluru_query.copy()
    query["lang"] = "kan"
    response = client.get("/api/v1/all", query_string=query)
    assert response.status_code == 200
    data = response.get_json()

    assert data["panchanga"]["tithi"] == "ಕೃಷ್ಣ ಅಷ್ಟಮಿ"
    assert data["panchanga"]["nakshatra"] == "ರೇವತಿ"
    assert data["panchanga"]["vara"] == "ಬುಧವಾರ"
    assert data["panchanga"]["karana"] == "ಕೌಲವ"
    assert data["panchanga"]["yoga"] == "ಅತಿಗಂಡ"
    assert data["panchanga"]["samvatsara"] == "ಪರಾಭವ"
    assert data["panchanga"]["ayana"] == "ಉತ್ತರಾಯಣ"
    assert data["panchanga"]["rutu"] == "ಗ್ರೀಷ್ಮ"
    assert data["panchanga"]["masa"] == "ಜ್ಯೇಷ್ಠ"
    assert data["panchanga"]["paksha"] == "ಕೃಷ್ಣ"
    assert data["moon"]["rasi"] == "ಮೀನ"
    assert data["sun"]["rasi"] == "ಮಿಥುನ"
    assert data["muhurta"]["rahu_kalam"]["name"] == "ರಾಹುಕಾಲ"
    assert data["muhurta"]["gulika"]["name"] == "ಗುಳಿಕ ಕಾಲ"
    assert data["muhurta"]["yamaganda"]["name"] == "ಯಮಗಂಡ"
    assert data["muhurta"]["abhijit"]["name"] == "ಅಭಿಜಿತ್ ಮುಹೂರ್ತ"
