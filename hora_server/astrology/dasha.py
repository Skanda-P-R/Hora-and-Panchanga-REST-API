"""Vimshottari Dasha calculation logic."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final

from hora_server.astrology.constants import (
    DASHA_LORDS,
    DASHA_YEARS,
    ENGLISH_RASIS,
    NAKSHATRAS,
)

RASI_NAMES: Final[tuple[str, ...]] = ENGLISH_RASIS


@dataclass(frozen=True)
class DashaPeriod:
    level: int
    lord: str
    start: datetime
    end: datetime
    duration_years: float
    sub_periods: tuple[DashaPeriod, ...]


@dataclass(frozen=True)
class MoonDetails:
    longitude: float
    degree_in_rasi: float
    rasi: str
    rasi_number: int
    nakshatra: str
    nakshatra_number: int
    nakshatra_lord: str


@dataclass(frozen=True)
class DashaBalance:
    lord: str
    total_years: float
    elapsed_years: float
    remaining_years: float
    elapsed_fraction: float
    remaining_fraction: float


@dataclass(frozen=True)
class ActiveDasha:
    mahadasha: str
    antardasha: str
    pratyantardasha: str | None


def calculate_dasha(
    moon_longitude: float,
    start_time: datetime,
    year_days: float = 365.25,
    depth: int = 2,
) -> tuple[MoonDetails, DashaBalance, tuple[DashaPeriod, ...], ActiveDasha]:
    # 1. Moon and Nakshatra
    long_360 = moon_longitude % 360
    nakshatra_width = 360.0 / 27.0
    nakshatra_idx = int(long_360 // nakshatra_width)
    nakshatra_name = NAKSHATRAS[nakshatra_idx]
    nakshatra_num = nakshatra_idx + 1

    lord_idx = nakshatra_idx % 9
    start_lord = DASHA_LORDS[lord_idx]

    rasi_num = int(long_360 // 30) + 1
    rasi_name = RASI_NAMES[rasi_num - 1]

    moon_details = MoonDetails(
        longitude=long_360,
        degree_in_rasi=long_360 % 30,
        rasi=rasi_name,
        rasi_number=rasi_num,
        nakshatra=nakshatra_name,
        nakshatra_number=nakshatra_num,
        nakshatra_lord=start_lord,
    )

    # 2. Dasha balance
    nakshatra_start = nakshatra_idx * nakshatra_width
    elapsed_deg = long_360 - nakshatra_start
    elapsed_frac = elapsed_deg / nakshatra_width
    remaining_frac = 1.0 - elapsed_frac

    total_years = float(DASHA_YEARS[start_lord])
    elapsed_years = elapsed_frac * total_years
    remaining_years = remaining_frac * total_years

    balance = DashaBalance(
        lord=start_lord,
        total_years=total_years,
        elapsed_years=round(elapsed_years, 4),
        remaining_years=round(remaining_years, 4),
        elapsed_fraction=round(elapsed_frac, 6),
        remaining_fraction=round(remaining_frac, 6),
    )

    # 3. Theoretical start time of first Mahadasha
    t_start = start_time - timedelta(days=elapsed_years * year_days)

    # 4. Generate dasha timeline
    timeline: list[DashaPeriod] = []
    current_time = t_start

    for i in range(10):
        m_lord_idx = (lord_idx + i) % 9
        m_lord = DASHA_LORDS[m_lord_idx]
        m_years = float(DASHA_YEARS[m_lord])
        m_duration = timedelta(days=m_years * year_days)
        m_end = current_time + m_duration

        antardashas: list[DashaPeriod] = []
        if depth >= 2:
            a_start = current_time
            for j in range(9):
                a_lord_idx = (m_lord_idx + j) % 9
                a_lord = DASHA_LORDS[a_lord_idx]
                a_years = (m_years * float(DASHA_YEARS[a_lord])) / 120.0
                a_duration = timedelta(days=a_years * year_days)
                a_end = a_start + a_duration

                pratyantardashas: list[DashaPeriod] = []
                if depth >= 3:
                    p_start = a_start
                    for k in range(9):
                        p_lord_idx = (a_lord_idx + k) % 9
                        p_lord = DASHA_LORDS[p_lord_idx]
                        p_years = (a_years * float(DASHA_YEARS[p_lord])) / 120.0
                        p_duration = timedelta(days=p_years * year_days)
                        p_end = p_start + p_duration

                        pratyantardashas.append(
                            DashaPeriod(
                                level=3,
                                lord=p_lord,
                                start=p_start,
                                end=p_end,
                                duration_years=round(p_years, 6),
                                sub_periods=(),
                            )
                        )
                        p_start = p_end

                antardashas.append(
                    DashaPeriod(
                        level=2,
                        lord=a_lord,
                        start=a_start,
                        end=a_end,
                        duration_years=round(a_years, 4),
                        sub_periods=tuple(pratyantardashas),
                    )
                )
                a_start = a_end

        timeline.append(
            DashaPeriod(
                level=1,
                lord=m_lord,
                start=current_time,
                end=m_end,
                duration_years=m_years,
                sub_periods=tuple(antardashas),
            )
        )
        current_time = m_end

    # 5. Determine active dasha at start_time
    active_mahadasha = ""
    active_antardasha = ""
    active_pratyantardasha = None

    for m in timeline:
        if m.start <= start_time < m.end:
            active_mahadasha = m.lord
            for a in m.sub_periods:
                if a.start <= start_time < a.end:
                    active_antardasha = a.lord
                    for p in a.sub_periods:
                        if p.start <= start_time < p.end:
                            active_pratyantardasha = p.lord
                            break
                    break
            break

    active = ActiveDasha(
        mahadasha=active_mahadasha,
        antardasha=active_antardasha,
        pratyantardasha=active_pratyantardasha,
    )

    return moon_details, balance, tuple(timeline), active
