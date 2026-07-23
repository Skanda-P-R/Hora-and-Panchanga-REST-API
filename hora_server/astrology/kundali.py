"""Current transit Kundali calculation using Swiss sidereal positions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

import swisseph as swe

from hora_server.astronomy.ephemeris import Ayanamsa, EphemerisEngine
from hora_server.astrology.constants import ENGLISH_RASIS


RASI_NAMES: Final[tuple[str, ...]] = ENGLISH_RASIS

PLANET_BODIES: Final[tuple[tuple[str, str, int], ...]] = (
    ("Sun", "Su", swe.SUN),
    ("Moon", "Mo", swe.MOON),
    ("Mars", "Ma", swe.MARS),
    ("Mercury", "Me", swe.MERCURY),
    ("Jupiter", "Ju", swe.JUPITER),
    ("Venus", "Ve", swe.VENUS),
    ("Saturn", "Sa", swe.SATURN),
    ("Rahu", "Ra", swe.MEAN_NODE),
)


@dataclass(frozen=True)
class KundaliLagna:
    rasi: str
    number: int
    longitude: float
    degree_in_rasi: float


@dataclass(frozen=True)
class KundaliPlanet:
    planet: str
    symbol: str
    longitude: float
    degree_in_rasi: float
    rasi: str
    rasi_number: int
    house: int
    retrograde: bool


@dataclass(frozen=True)
class KundaliHouse:
    house: int
    rasi: str
    rasi_number: int
    planets: tuple[str, ...]


@dataclass(frozen=True)
class Kundali:
    lagna: KundaliLagna
    houses: tuple[KundaliHouse, ...]
    planets: tuple[KundaliPlanet, ...]


def _rasi_number(longitude: float) -> int:
    return int((longitude % 360) // 30) + 1


def _rasi_name(number: int) -> str:
    return RASI_NAMES[number - 1]


def _degree_in_rasi(longitude: float) -> float:
    return longitude % 30


def _house_for_rasi(rasi_number: int, lagna_number: int) -> int:
    return ((rasi_number - lagna_number) % 12) + 1


def _planet(
    name: str,
    symbol: str,
    longitude: float,
    speed_longitude: float,
    lagna_number: int,
) -> KundaliPlanet:
    rasi_number = _rasi_number(longitude)
    return KundaliPlanet(
        planet=name,
        symbol=symbol,
        longitude=longitude % 360,
        degree_in_rasi=_degree_in_rasi(longitude),
        rasi=_rasi_name(rasi_number),
        rasi_number=rasi_number,
        house=_house_for_rasi(rasi_number, lagna_number),
        retrograde=speed_longitude < 0,
    )


def calculate_kundali(
    instant: datetime,
    latitude: float,
    longitude: float,
    engine: EphemerisEngine,
    ayanamsa: Ayanamsa,
) -> Kundali:
    ascendant = engine.sidereal_ascendant(
        instant, ayanamsa, latitude, longitude
    )
    lagna_number = _rasi_number(ascendant)
    lagna = KundaliLagna(
        rasi=_rasi_name(lagna_number),
        number=lagna_number,
        longitude=ascendant,
        degree_in_rasi=_degree_in_rasi(ascendant),
    )

    body_positions = engine.sidereal_body_positions(
        instant,
        ayanamsa,
        tuple((name, body) for name, _, body in PLANET_BODIES),
    )
    planets = [
        _planet(
            name,
            symbol,
            body_positions[name].longitude,
            body_positions[name].speed_longitude,
            lagna_number,
        )
        for name, symbol, _ in PLANET_BODIES
    ]

    rahu = body_positions["Rahu"]
    planets.append(
        _planet(
            "Ketu",
            "Ke",
            rahu.longitude + 180,
            rahu.speed_longitude,
            lagna_number,
        )
    )

    planet_names_by_house: dict[int, list[str]] = {house: [] for house in range(1, 13)}
    for planet in planets:
        planet_names_by_house[planet.house].append(planet.planet)

    houses = tuple(
        KundaliHouse(
            house=house,
            rasi=_rasi_name(((lagna_number + house - 2) % 12) + 1),
            rasi_number=((lagna_number + house - 2) % 12) + 1,
            planets=tuple(planet_names_by_house[house]),
        )
        for house in range(1, 13)
    )
    return Kundali(lagna=lagna, houses=houses, planets=tuple(planets))
