"""Offline coordinate-to-timezone resolution."""

from __future__ import annotations

from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from timezonefinder import TimezoneFinder

from .errors import ApiError


class TimezoneResolver:
    def __init__(self) -> None:
        self._finder = TimezoneFinder(in_memory=True)

    @staticmethod
    def validate(name: str) -> ZoneInfo:
        try:
            return ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ApiError(
                "timezone must be a valid IANA timezone name",
                code="invalid_timezone",
                details={"parameter": "timezone", "value": name},
            ) from exc

    @lru_cache(maxsize=4096)
    def from_coordinates(self, latitude: float, longitude: float) -> ZoneInfo:
        name = self._finder.timezone_at(lng=longitude, lat=latitude)
        if not name:
            raise ApiError(
                "No timezone could be resolved for these coordinates; provide timezone",
                code="timezone_not_found",
                details={"latitude": latitude, "longitude": longitude},
            )
        return self.validate(name)

    def resolve(
        self, latitude: float, longitude: float, requested: str | None
    ) -> ZoneInfo:
        if requested and requested.strip():
            return self.validate(requested.strip())
        return self.from_coordinates(latitude, longitude)

