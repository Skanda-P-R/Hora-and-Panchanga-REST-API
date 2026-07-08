"""Unequal planetary-hour calculations for a Vedic solar day."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from hora_server.astronomy.sunrise import SolarDay
from hora_server.utils.datetime import add_elapsed, duration_seconds

from .constants import PLANET_SEQUENCE, PLANET_SYMBOLS, WEEKDAY_LORDS


@dataclass(frozen=True)
class PlanetaryHour:
    number: int
    period: str
    period_number: int
    planet: str
    symbol: str
    start: datetime
    end: datetime


def planetary_hours(solar_day: SolarDay) -> list[PlanetaryHour]:
    first_planet = WEEKDAY_LORDS[solar_day.date.weekday()]
    sequence_offset = PLANET_SEQUENCE.index(first_planet)
    day_length = solar_day.day_duration_seconds / 12
    night_length = solar_day.night_duration_seconds / 12
    hours: list[PlanetaryHour] = []

    for number in range(24):
        if number < 12:
            period = "day"
            period_number = number + 1
            start = add_elapsed(solar_day.sunrise, number * day_length)
            end = add_elapsed(solar_day.sunrise, (number + 1) * day_length)
        else:
            period = "night"
            period_number = number - 11
            night_index = number - 12
            start = add_elapsed(solar_day.sunset, night_index * night_length)
            end = add_elapsed(solar_day.sunset, (night_index + 1) * night_length)
        planet = PLANET_SEQUENCE[(sequence_offset + number) % len(PLANET_SEQUENCE)]
        hours.append(
            PlanetaryHour(
                number=number + 1,
                period=period,
                period_number=period_number,
                planet=planet,
                symbol=PLANET_SYMBOLS[planet],
                start=start,
                end=end,
            )
        )
    return hours


def current_planetary_hour(
    instant: datetime, hours: list[PlanetaryHour]
) -> tuple[PlanetaryHour, str]:
    instant_utc = instant.astimezone(UTC)
    for index, hour in enumerate(hours):
        if (
            hour.start.astimezone(UTC)
            <= instant_utc
            < hour.end.astimezone(UTC)
        ):
            next_planet = PLANET_SEQUENCE[
                (PLANET_SEQUENCE.index(hour.planet) + 1) % len(PLANET_SEQUENCE)
            ]
            return hour, next_planet
    raise ValueError("instant is outside the supplied Vedic solar day")


def remaining_seconds(instant: datetime, hour: PlanetaryHour) -> int:
    return max(0, int(duration_seconds(instant, hour.end)))
