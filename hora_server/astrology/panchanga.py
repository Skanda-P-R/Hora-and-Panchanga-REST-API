"""Five-limb Panchanga classification and transition solving."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from math import floor
from typing import Callable, Final

from hora_server.astronomy.ephemeris import Ayanamsa, EphemerisEngine, Positions

from .constants import (
    NAKSHATRAS,
    PAKSHA_TITHIS,
    RASHIS,
    REPEATING_KARANAS,
    VARA_NAMES,
    WEEKDAY_NAMES,
    YOGAS,
    MASAS,
    RUTUS,
    SAMVATSARAS,
)


NAKSHATRA_SPAN: Final[float] = 360 / 27
PADA_SPAN: Final[float] = 360 / 108


@dataclass(frozen=True)
class Limb:
    index: int
    number: int
    name: str
    longitude: float
    progress: float
    ends_at: datetime | None = None
    extra: dict[str, object] | None = None


@dataclass(frozen=True)
class Panchanga:
    tithi: Limb
    nakshatra: Limb
    yoga: Limb
    karana: Limb
    vara: str
    vara_sanskrit: str
    sun_rasi: str
    moon_rasi: str
    moon_pada: int
    positions: Positions
    samvatsara: str
    ayana: str
    rutu: str
    masa: str
    paksha: str


def tithi_name(index: int) -> tuple[str, str]:
    if index < 14:
        return f"Shukla {PAKSHA_TITHIS[index]}", "Shukla"
    if index == 14:
        return "Purnima", "Shukla"
    if index < 29:
        return f"Krishna {PAKSHA_TITHIS[index - 15]}", "Krishna"
    return "Amavasya", "Krishna"


def karana_name(index: int) -> str:
    if index == 0:
        return "Kimstughna"
    if 1 <= index <= 56:
        return REPEATING_KARANAS[(index - 1) % len(REPEATING_KARANAS)]
    return ("Shakuni", "Chatushpada", "Naga")[index - 57]


def _index(value: float, span: float, count: int) -> int:
    return min(count - 1, floor((value % 360) / span))


def _progress(value: float, span: float) -> float:
    return (value % span) / span


def phase_value(positions: Positions, kind: str) -> float:
    if kind in {"tithi", "karana"}:
        return (positions.moon_tropical - positions.sun_tropical) % 360
    if kind == "nakshatra":
        return positions.moon_sidereal % 360
    if kind == "yoga":
        return (positions.moon_sidereal + positions.sun_sidereal) % 360
    raise ValueError(f"Unknown Panchanga limb: {kind}")


def phase_index(positions: Positions, kind: str) -> int:
    spans = {"tithi": 12.0, "karana": 6.0, "nakshatra": NAKSHATRA_SPAN, "yoga": NAKSHATRA_SPAN}
    counts = {"tithi": 30, "karana": 60, "nakshatra": 27, "yoga": 27}
    return _index(phase_value(positions, kind), spans[kind], counts[kind])


def find_next_transition(
    instant: datetime,
    kind: str,
    engine: EphemerisEngine,
    ayanamsa: Ayanamsa,
) -> datetime:
    """Find the next classification boundary to within one elapsed second."""

    initial = phase_index(engine.positions(instant, ayanamsa), kind)
    output_timezone = instant.tzinfo
    lower = instant.astimezone(UTC)
    upper = lower
    # No limb is normally shorter than ~9 hours; a 3-hour scan cannot skip a
    # complete element and is still robust around the Moon's speed extremes.
    step = timedelta(hours=3)
    for _ in range(32):
        upper += step
        if phase_index(engine.positions(upper, ayanamsa), kind) != initial:
            break
        lower = upper
    else:
        raise RuntimeError(f"Could not bracket next {kind} transition")

    while (upper - lower).total_seconds() > 1:
        midpoint = lower + (upper - lower) / 2
        if phase_index(engine.positions(midpoint, ayanamsa), kind) == initial:
            lower = midpoint
        else:
            upper = midpoint
    return upper.astimezone(output_timezone)


def calculate_panchanga(
    instant: datetime,
    vedic_weekday: int,
    engine: EphemerisEngine,
    ayanamsa: Ayanamsa,
    include_transitions: bool = True,
) -> Panchanga:
    positions = engine.positions(instant, ayanamsa)
    elongation = phase_value(positions, "tithi")
    tithi_index = _index(elongation, 12, 30)
    tithi, paksha = tithi_name(tithi_index)
    karana_index = _index(elongation, 6, 60)
    nakshatra_index = _index(positions.moon_sidereal, NAKSHATRA_SPAN, 27)
    yoga_value = phase_value(positions, "yoga")
    yoga_index = _index(yoga_value, NAKSHATRA_SPAN, 27)
    pada = _index(positions.moon_sidereal % NAKSHATRA_SPAN, PADA_SPAN, 4) + 1

    transition: Callable[[str], datetime | None]
    if include_transitions:
        transition = lambda kind: find_next_transition(
            instant, kind, engine, ayanamsa
        )
    else:
        transition = lambda kind: None

    # Solve conjunctions to find containing Amanta month
    NM_prev = engine.conjunction(instant, -1)
    NM_next = engine.conjunction(instant, 1)

    pos_prev = engine.positions(NM_prev, ayanamsa)
    pos_next = engine.positions(NM_next, ayanamsa)

    R_prev = int(pos_prev.sun_sidereal // 30)
    R_next = int(pos_next.sun_sidereal // 30)

    is_adhika = R_prev == R_next
    month_index = (R_prev + 1) % 12 if is_adhika else R_next

    masa = f"Adhika {MASAS[month_index]}" if is_adhika else MASAS[month_index]
    rutu = RUTUS[month_index // 2]

    sun_sid = positions.sun_sidereal
    ayana = "Dakshinayana" if 90 <= sun_sid < 270 else "Uttarayana"

    year = instant.year
    if month_index in (10, 11) and instant.month <= 4:
        shaka_year = year - 79
    else:
        shaka_year = year - 78

    samvatsara_index = (shaka_year + 11) % 60
    samvatsara = SAMVATSARAS[samvatsara_index]

    return Panchanga(
        tithi=Limb(
            tithi_index,
            tithi_index + 1,
            tithi,
            elongation,
            _progress(elongation, 12),
            transition("tithi"),
            {
                "paksha": paksha,
                "lunar_day_number": tithi_index + 1,
                "paksha_day_number": (
                    tithi_index + 1 if tithi_index < 15 else tithi_index - 14
                ),
            },
        ),
        nakshatra=Limb(
            nakshatra_index,
            nakshatra_index + 1,
            NAKSHATRAS[nakshatra_index],
            positions.moon_sidereal,
            _progress(positions.moon_sidereal, NAKSHATRA_SPAN),
            transition("nakshatra"),
            {"pada": pada},
        ),
        yoga=Limb(
            yoga_index,
            yoga_index + 1,
            YOGAS[yoga_index],
            yoga_value,
            _progress(yoga_value, NAKSHATRA_SPAN),
            transition("yoga"),
        ),
        karana=Limb(
            karana_index,
            karana_index + 1,
            karana_name(karana_index),
            elongation,
            _progress(elongation, 6),
            transition("karana"),
        ),
        vara=WEEKDAY_NAMES[vedic_weekday],
        vara_sanskrit=VARA_NAMES[vedic_weekday],
        sun_rasi=RASHIS[_index(positions.sun_sidereal, 30, 12)],
        moon_rasi=RASHIS[_index(positions.moon_sidereal, 30, 12)],
        moon_pada=pada,
        positions=positions,
        samvatsara=samvatsara,
        ayana=ayana,
        rutu=rutu,
        masa=masa,
        paksha=paksha,
    )
