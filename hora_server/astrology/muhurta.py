"""Daylight-derived Kalam and Abhijit intervals."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Final

from hora_server.astronomy.sunrise import SolarDay
from hora_server.utils.datetime import add_elapsed


@dataclass(frozen=True)
class MuhurtaInterval:
    name: str
    start: datetime
    end: datetime
    segment: int | None = None
    traditionally_auspicious: bool | None = None
    note: str | None = None


# Python weekday order: Monday=0 through Sunday=6; values are one-based
# eighths of the actual sunrise-to-sunset interval.
RAHU_SEGMENTS: Final[tuple[int, ...]] = (2, 7, 5, 6, 4, 3, 8)
GULIKA_SEGMENTS: Final[tuple[int, ...]] = (6, 5, 4, 3, 2, 1, 7)
YAMAGANDA_SEGMENTS: Final[tuple[int, ...]] = (4, 3, 2, 1, 7, 6, 5)


def _eighth(
    name: str, solar_day: SolarDay, segment: int, auspicious: bool = False
) -> MuhurtaInterval:
    eighth = solar_day.day_duration_seconds / 8
    return MuhurtaInterval(
        name=name,
        start=add_elapsed(solar_day.sunrise, (segment - 1) * eighth),
        end=add_elapsed(solar_day.sunrise, segment * eighth),
        segment=segment,
        traditionally_auspicious=auspicious,
    )


def calculate_muhurta(solar_day: SolarDay) -> dict[str, MuhurtaInterval]:
    weekday = solar_day.date.weekday()
    abhijit_start = add_elapsed(
        solar_day.sunrise, solar_day.day_duration_seconds * 7 / 15
    )
    abhijit_end = add_elapsed(
        solar_day.sunrise, solar_day.day_duration_seconds * 8 / 15
    )
    wednesday = weekday == 2
    return {
        "rahu_kalam": _eighth(
            "Rahu Kalam", solar_day, RAHU_SEGMENTS[weekday]
        ),
        "gulika": _eighth("Gulika Kalam", solar_day, GULIKA_SEGMENTS[weekday]),
        "yamaganda": _eighth(
            "Yamaganda", solar_day, YAMAGANDA_SEGMENTS[weekday]
        ),
        "abhijit": MuhurtaInterval(
            name="Abhijit Muhurta",
            start=abhijit_start,
            end=abhijit_end,
            traditionally_auspicious=not wednesday,
            note=(
                "Traditionally avoided on Wednesday in common muhurta practice."
                if wednesday
                else None
            ),
        ),
    }

