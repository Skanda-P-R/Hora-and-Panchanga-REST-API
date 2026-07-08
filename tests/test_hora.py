from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from hora_server.astronomy.sunrise import SolarDay
from hora_server.astrology.constants import PLANET_SEQUENCE
from hora_server.astrology.hora import current_planetary_hour, planetary_hours


def _solar_day(local_date: date, timezone: ZoneInfo = ZoneInfo("UTC")) -> SolarDay:
    sunrise = datetime.combine(local_date, datetime.min.time(), timezone).replace(
        hour=6
    )
    sunset = sunrise.replace(hour=18)
    next_sunrise = datetime.combine(
        date.fromordinal(local_date.toordinal() + 1),
        datetime.min.time(),
        timezone,
    ).replace(hour=6)
    return SolarDay(local_date, sunrise, sunset, next_sunrise)


def test_planetary_hours_tile_a_monday_without_gaps():
    solar_day = _solar_day(date(2026, 7, 6))  # Monday
    hours = planetary_hours(solar_day)

    assert len(hours) == 24
    assert hours[0].planet == "Moon"
    assert hours[0].start == solar_day.sunrise
    assert hours[11].end == solar_day.sunset
    assert hours[12].start == solar_day.sunset
    assert hours[-1].end == solar_day.next_sunrise
    assert all(left.end == right.start for left, right in zip(hours, hours[1:]))
    assert all((hour.end - hour.start).total_seconds() == 3600 for hour in hours)

    first_offset = PLANET_SEQUENCE.index("Moon")
    assert [hour.planet for hour in hours] == [
        PLANET_SEQUENCE[(first_offset + index) % 7] for index in range(24)
    ]


def test_first_hora_matches_all_seven_weekday_lords():
    expected = ("Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Sun")
    monday = date(2026, 7, 6)
    for offset, lord in enumerate(expected):
        assert planetary_hours(_solar_day(date.fromordinal(monday.toordinal() + offset)))[
            0
        ].planet == lord


def test_exact_sunset_belongs_to_first_night_hora():
    solar_day = _solar_day(date(2026, 7, 6))
    hours = planetary_hours(solar_day)

    current, _ = current_planetary_hour(solar_day.sunset, hours)

    assert current.period == "night"
    assert current.period_number == 1


def test_hour_after_final_hour_is_next_weekday_lord():
    solar_day = _solar_day(date(2026, 7, 6))
    hours = planetary_hours(solar_day)
    instant = hours[-1].start.astimezone(UTC)

    current, next_planet = current_planetary_hour(instant, hours)

    assert current.number == 24
    assert next_planet == "Mars"  # Tuesday's first hora


def test_dst_night_is_divided_by_elapsed_time():
    timezone = ZoneInfo("America/New_York")
    solar_day = SolarDay(
        date(2026, 3, 7),
        datetime(2026, 3, 7, 6, tzinfo=timezone),
        datetime(2026, 3, 7, 18, tzinfo=timezone),
        datetime(2026, 3, 8, 6, tzinfo=timezone),
    )

    hours = planetary_hours(solar_day)

    # The spring-forward night contains 11 elapsed hours, even though its wall
    # clock endpoints look 12 hours apart.
    assert solar_day.night_duration_seconds == 11 * 3600
    assert all(
        abs(
            (
                hour.end.astimezone(UTC) - hour.start.astimezone(UTC)
            ).total_seconds()
            - 3300
        )
        < 1e-6
        for hour in hours[12:]
    )


def test_instant_outside_cycle_is_rejected():
    solar_day = _solar_day(date(2026, 7, 6))
    with pytest.raises(ValueError):
        current_planetary_hour(solar_day.next_sunrise, planetary_hours(solar_day))
