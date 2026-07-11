"""Thread-safe Swiss Ephemeris access for Sun and Moon calculations."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final

import swisseph as swe

from hora_server.utils.errors import ApiError


@dataclass(frozen=True)
class Ayanamsa:
    key: str
    display_name: str
    swiss_mode: int


AYANAMSAS: Final[dict[str, Ayanamsa]] = {
    "lahiri": Ayanamsa("lahiri", "Lahiri", swe.SIDM_LAHIRI),
    "raman": Ayanamsa("raman", "Raman", swe.SIDM_RAMAN),
    "krishnamurti": Ayanamsa(
        "krishnamurti", "Krishnamurti", swe.SIDM_KRISHNAMURTI
    ),
    "fagan_bradley": Ayanamsa(
        "fagan_bradley", "Fagan-Bradley", swe.SIDM_FAGAN_BRADLEY
    ),
}

AYANAMSA_ALIASES: Final[dict[str, str]] = {
    "fagan": "fagan_bradley",
    "fagan-bradley": "fagan_bradley",
    "kp": "krishnamurti",
    "chitrapaksha": "lahiri",
}


@dataclass(frozen=True)
class Positions:
    julian_day_ut: float
    sun_tropical: float
    moon_tropical: float
    sun_sidereal: float
    moon_sidereal: float
    ayanamsa_degrees: float
    ephemeris: str


@dataclass(frozen=True)
class BodyPosition:
    longitude: float
    speed_longitude: float
    ephemeris: str


class EphemerisEngine:
    """Serializes process-global Swiss configuration around each calculation."""

    _lock = threading.RLock()

    def __init__(
        self, ephemeris_path: str | None = None, strict_swiss: bool = False
    ) -> None:
        self.ephemeris_path = ephemeris_path
        self.strict_swiss = strict_swiss
        with self._lock:
            if ephemeris_path:
                if not os.path.isdir(ephemeris_path):
                    raise RuntimeError(
                        f"SE_EPHEMERIS_PATH is not a directory: {ephemeris_path}"
                    )
                swe.set_ephe_path(ephemeris_path)

    @staticmethod
    def resolve_ayanamsa(value: str | None, default: str = "lahiri") -> Ayanamsa:
        normalized = (value or default).strip().lower().replace(" ", "_")
        normalized = AYANAMSA_ALIASES.get(normalized, normalized)
        try:
            return AYANAMSAS[normalized]
        except KeyError as exc:
            raise ApiError(
                "ayanamsa is not supported",
                code="invalid_ayanamsa",
                details={
                    "parameter": "ayanamsa",
                    "value": value,
                    "supported": sorted(AYANAMSAS),
                },
            ) from exc

    @staticmethod
    def julian_day(value: datetime) -> float:
        utc = value.astimezone(UTC)
        hour = (
            utc.hour
            + utc.minute / 60
            + utc.second / 3600
            + utc.microsecond / 3_600_000_000
        )
        return swe.julday(utc.year, utc.month, utc.day, hour, swe.GREG_CAL)

    @staticmethod
    def datetime_from_julian_day(julian_day: float) -> datetime:
        year, month, day, decimal_hour = swe.revjul(julian_day, swe.GREG_CAL)
        # Constructing from midnight plus seconds avoids 59.999999 rounding
        # artifacts and correctly carries into the next date.
        midnight = datetime(year, month, day, tzinfo=UTC)
        return midnight + timedelta(seconds=decimal_hour * 3600)

    @staticmethod
    def _backend_name(flags: int) -> str:
        if flags & swe.FLG_JPLEPH:
            return "jpl"
        if flags & swe.FLG_SWIEPH:
            return "swiss"
        if flags & swe.FLG_MOSEPH:
            return "moshier"
        return "unknown"

    def positions(self, value: datetime, ayanamsa: Ayanamsa) -> Positions:
        julian_day = self.julian_day(value)
        tropical_flags = swe.FLG_SWIEPH | swe.FLG_SPEED
        sidereal_flags = tropical_flags | swe.FLG_SIDEREAL

        with self._lock:
            if self.ephemeris_path:
                swe.set_ephe_path(self.ephemeris_path)
            swe.set_sid_mode(ayanamsa.swiss_mode, 0, 0)
            sun_tropical, sun_flags = swe.calc_ut(
                julian_day, swe.SUN, tropical_flags
            )
            moon_tropical, moon_flags = swe.calc_ut(
                julian_day, swe.MOON, tropical_flags
            )
            sun_sidereal, sun_sidereal_flags = swe.calc_ut(
                julian_day, swe.SUN, sidereal_flags
            )
            moon_sidereal, moon_sidereal_flags = swe.calc_ut(
                julian_day, swe.MOON, sidereal_flags
            )
            ayanamsa_flags, ayanamsa_degrees = swe.get_ayanamsa_ex_ut(
                julian_day, swe.FLG_SWIEPH
            )

        backends = {
            self._backend_name(flag)
            for flag in (
                sun_flags,
                moon_flags,
                sun_sidereal_flags,
                moon_sidereal_flags,
                ayanamsa_flags,
            )
        }
        backend = backends.pop() if len(backends) == 1 else "+".join(sorted(backends))
        if self.strict_swiss and backend != "swiss":
            raise ApiError(
                "Swiss Ephemeris data files are unavailable and fallback is disabled",
                code="ephemeris_unavailable",
                status_code=503,
                details={
                    "backend": backend,
                    "hint": "Set SE_EPHEMERIS_PATH to a directory containing Swiss .se1 files",
                },
            )

        return Positions(
            julian_day_ut=julian_day,
            sun_tropical=sun_tropical[0] % 360,
            moon_tropical=moon_tropical[0] % 360,
            sun_sidereal=sun_sidereal[0] % 360,
            moon_sidereal=moon_sidereal[0] % 360,
            ayanamsa_degrees=ayanamsa_degrees,
            ephemeris=backend,
        )

    def sidereal_body_positions(
        self, value: datetime, ayanamsa: Ayanamsa, bodies: tuple[tuple[str, int], ...]
    ) -> dict[str, BodyPosition]:
        julian_day = self.julian_day(value)
        flags = swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL
        calculated: dict[str, tuple[tuple[float, ...], int]] = {}

        with self._lock:
            if self.ephemeris_path:
                swe.set_ephe_path(self.ephemeris_path)
            swe.set_sid_mode(ayanamsa.swiss_mode, 0, 0)
            for name, body in bodies:
                coordinates, returned_flags = swe.calc_ut(julian_day, body, flags)
                calculated[name] = (coordinates, returned_flags)

        backends = {
            self._backend_name(returned_flags)
            for _, returned_flags in calculated.values()
        }
        backend = backends.pop() if len(backends) == 1 else "+".join(sorted(backends))
        if self.strict_swiss and backend != "swiss":
            raise ApiError(
                "Swiss Ephemeris data files are unavailable and fallback is disabled",
                code="ephemeris_unavailable",
                status_code=503,
                details={
                    "backend": backend,
                    "hint": "Set SE_EPHEMERIS_PATH to a directory containing Swiss .se1 files",
                },
            )

        return {
            name: BodyPosition(
                longitude=coordinates[0] % 360,
                speed_longitude=coordinates[3],
                ephemeris=backend,
            )
            for name, (coordinates, _) in calculated.items()
        }

    def sidereal_ascendant(
        self,
        value: datetime,
        ayanamsa: Ayanamsa,
        latitude: float,
        longitude: float,
        house_system: bytes = b"W",
    ) -> float:
        julian_day = self.julian_day(value)
        flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
        try:
            with self._lock:
                if self.ephemeris_path:
                    swe.set_ephe_path(self.ephemeris_path)
                swe.set_sid_mode(ayanamsa.swiss_mode, 0, 0)
                _, ascmc = swe.houses_ex(
                    julian_day, latitude, longitude, house_system, flags
                )
        except swe.Error as exc:
            raise ApiError(
                "Ascendant could not be calculated for this date and location",
                code="kundali_unavailable",
                status_code=422,
                details={"reason": str(exc)},
            ) from exc
        return ascmc[swe.ASC] % 360

    def rise_or_set(
        self,
        start: datetime,
        latitude: float,
        longitude: float,
        elevation_meters: float,
        event_flag: int,
        pressure_hpa: float,
        temperature_c: float,
    ) -> datetime:
        julian_day = self.julian_day(start)
        geopos = (longitude, latitude, elevation_meters)
        try:
            with self._lock:
                if self.ephemeris_path:
                    swe.set_ephe_path(self.ephemeris_path)
                result, returned_jd = swe.rise_trans(
                    julian_day,
                    swe.SUN,
                    event_flag,
                    geopos,
                    pressure_hpa,
                    temperature_c,
                    swe.FLG_SWIEPH,
                )
        except swe.Error as exc:
            raise ApiError(
                "The requested solar event does not occur for this date and location",
                code="solar_event_unavailable",
                status_code=422,
                details={"reason": str(exc)},
            ) from exc

        if result < 0:
            raise ApiError(
                "The requested solar event does not occur for this date and location",
                code="solar_event_unavailable",
                status_code=422,
            )
        return self.datetime_from_julian_day(returned_jd[0])

    @property
    def version(self) -> str:
        return str(swe.version)
