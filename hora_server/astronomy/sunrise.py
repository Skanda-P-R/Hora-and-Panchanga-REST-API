"""Location-aware solar events and Vedic-day selection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import swisseph as swe

from hora_server.utils.datetime import add_elapsed, duration_seconds
from hora_server.utils.errors import ApiError

from .ephemeris import EphemerisEngine


@dataclass(frozen=True)
class SolarDay:
    date: date
    sunrise: datetime
    sunset: datetime
    next_sunrise: datetime
    meridian_transit: datetime | None = None

    @property
    def daylight_midpoint(self) -> datetime:
        return add_elapsed(
            self.sunrise, duration_seconds(self.sunrise, self.sunset) / 2
        )

    @property
    def solar_noon(self) -> datetime:
        return self.meridian_transit or self.daylight_midpoint

    @property
    def day_duration_seconds(self) -> float:
        return duration_seconds(self.sunrise, self.sunset)

    @property
    def night_duration_seconds(self) -> float:
        return duration_seconds(self.sunset, self.next_sunrise)


class SolarCalculator:
    def __init__(
        self,
        engine: EphemerisEngine,
        elevation_meters: float = 0,
        pressure_hpa: float = 0,
        temperature_c: float = 15,
    ) -> None:
        self.engine = engine
        self.elevation_meters = elevation_meters
        self.pressure_hpa = pressure_hpa
        self.temperature_c = temperature_c

    @staticmethod
    def _search_start(local_date: date, timezone: ZoneInfo) -> datetime:
        # Swiss searches strictly after the supplied JD. One second before
        # local midnight includes an event occurring exactly at midnight.
        local_midnight = datetime.combine(local_date, time.min, timezone)
        return local_midnight.astimezone(UTC) - timedelta(seconds=1)

    def event_for_date(
        self,
        local_date: date,
        latitude: float,
        longitude: float,
        timezone: ZoneInfo,
        event_flag: int,
    ) -> datetime:
        event_utc = self.engine.rise_or_set(
            self._search_start(local_date, timezone),
            latitude,
            longitude,
            self.elevation_meters,
            event_flag,
            self.pressure_hpa,
            self.temperature_c,
        )
        event_local = event_utc.astimezone(timezone)
        if event_local.date() != local_date:
            # Near the date line or in polar transition seasons, the first
            # event found can fall outside the requested civil day.
            raise ApiError(
                "A sunrise or sunset does not occur on the requested local date",
                code="solar_event_unavailable",
                status_code=422,
                details={"date": local_date.isoformat(), "timezone": timezone.key},
            )
        return event_local

    def _event_after(
        self,
        start: datetime,
        latitude: float,
        longitude: float,
        timezone: ZoneInfo,
        event_flag: int,
    ) -> datetime:
        return self.engine.rise_or_set(
            start.astimezone(UTC),
            latitude,
            longitude,
            self.elevation_meters,
            event_flag,
            self.pressure_hpa,
            self.temperature_c,
        ).astimezone(timezone)

    def for_date(
        self,
        local_date: date,
        latitude: float,
        longitude: float,
        timezone: ZoneInfo,
    ) -> SolarDay:
        sunrise = self.event_for_date(
            local_date,
            latitude,
            longitude,
            timezone,
            swe.CALC_RISE | swe.BIT_HINDU_RISING,
        )
        sunset = self._event_after(
            sunrise,
            latitude,
            longitude,
            timezone,
            swe.CALC_SET | swe.BIT_HINDU_RISING,
        )
        meridian_transit = self._event_after(
            sunrise,
            latitude,
            longitude,
            timezone,
            swe.CALC_MTRANSIT,
        )
        next_sunrise = self._event_after(
            sunset,
            latitude,
            longitude,
            timezone,
            swe.CALC_RISE | swe.BIT_HINDU_RISING,
        )
        sunrise_utc = sunrise.astimezone(UTC)
        sunset_utc = sunset.astimezone(UTC)
        transit_utc = meridian_transit.astimezone(UTC)
        next_sunrise_utc = next_sunrise.astimezone(UTC)
        expected_next_date = local_date + timedelta(days=1)
        if not (
            sunrise_utc < transit_utc < sunset_utc < next_sunrise_utc
            and sunset.date() == local_date
            and next_sunrise.date() == expected_next_date
        ):
            raise ApiError(
                "This location does not have one ordered sunrise/sunset cycle on the requested dates",
                code="solar_event_unavailable",
                status_code=422,
                details={
                    "date": local_date.isoformat(),
                    "sunrise": sunrise.isoformat(),
                    "solar_transit": meridian_transit.isoformat(),
                    "sunset": sunset.isoformat(),
                    "next_sunrise": next_sunrise.isoformat(),
                },
            )
        return SolarDay(
            local_date, sunrise, sunset, next_sunrise, meridian_transit
        )

    def containing_vedic_day(
        self,
        instant: datetime,
        latitude: float,
        longitude: float,
        timezone: ZoneInfo,
    ) -> SolarDay:
        local = instant.astimezone(timezone)
        today = self.for_date(local.date(), latitude, longitude, timezone)
        if local.astimezone(UTC) >= today.sunrise.astimezone(UTC):
            return today
        previous = self.for_date(
            local.date() - timedelta(days=1), latitude, longitude, timezone
        )
        # Both searches describe the same physical sunrise, but independent
        # Swiss root searches can differ by a few microseconds. Reuse today's
        # value as the previous cycle's exclusive end so the boundary is
        # exactly gap-free.
        return SolarDay(
            previous.date,
            previous.sunrise,
            previous.sunset,
            today.sunrise,
            previous.meridian_transit,
        )
