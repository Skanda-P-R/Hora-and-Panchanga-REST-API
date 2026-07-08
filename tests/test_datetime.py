from __future__ import annotations

from datetime import UTC
from zoneinfo import ZoneInfo

import pytest

from hora_server.utils.datetime import parse_iso_datetime
from hora_server.utils.errors import ApiError


def test_date_only_means_local_noon():
    value = parse_iso_datetime("2026-07-08", ZoneInfo("Asia/Kolkata"))
    assert (value.hour, value.minute) == (12, 0)
    assert value.utcoffset().total_seconds() == 19_800


def test_offset_timestamp_is_converted_to_location_timezone():
    value = parse_iso_datetime("2026-07-08T06:30:00Z", ZoneInfo("Asia/Kolkata"))
    assert (value.hour, value.minute) == (12, 0)
    assert value.astimezone(UTC).hour == 6


def test_nonexistent_dst_time_is_rejected():
    with pytest.raises(ApiError) as error:
        parse_iso_datetime("2026-03-08T02:30:00", ZoneInfo("America/New_York"))
    assert error.value.code == "nonexistent_local_datetime"


def test_ambiguous_dst_time_requires_offset():
    with pytest.raises(ApiError) as error:
        parse_iso_datetime("2026-11-01T01:30:00", ZoneInfo("America/New_York"))
    assert error.value.code == "ambiguous_local_datetime"


def test_ambiguous_time_with_offset_is_accepted():
    value = parse_iso_datetime(
        "2026-11-01T01:30:00-04:00", ZoneInfo("America/New_York")
    )
    assert value.fold == 0


def test_skipped_civil_date_is_rejected():
    with pytest.raises(ApiError) as error:
        parse_iso_datetime("2011-12-30", ZoneInfo("Pacific/Apia"))
    assert error.value.code == "nonexistent_local_datetime"


def test_timezone_conversion_overflow_is_typed():
    with pytest.raises(ApiError) as error:
        parse_iso_datetime(
            "9999-12-31T23:59:59-12:00", ZoneInfo("Asia/Kolkata")
        )
    assert error.value.code == "datetime_out_of_range"
    assert error.value.status_code == 422
