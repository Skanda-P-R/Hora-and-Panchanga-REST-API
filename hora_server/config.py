"""Application configuration sourced from environment variables."""

from __future__ import annotations

import os
from pathlib import Path


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    _BUNDLED_EPHEMERIS_PATH = str(Path(__file__).resolve().parent / "ephe")
    DEFAULT_AYANAMSA = os.getenv("DEFAULT_AYANAMSA", "lahiri")
    EPHEMERIS_PATH = os.getenv("SE_EPHEMERIS_PATH", _BUNDLED_EPHEMERIS_PATH)
    STRICT_SWISS_EPHEMERIS = _as_bool(
        os.getenv("SWISS_EPHEMERIS_STRICT"), default=True
    )
    OBSERVER_ELEVATION_METERS = float(os.getenv("OBSERVER_ELEVATION_METERS", "0"))
    ATMOSPHERIC_PRESSURE_HPA = float(os.getenv("ATMOSPHERIC_PRESSURE_HPA", "0"))
    ATMOSPHERIC_TEMPERATURE_C = float(os.getenv("ATMOSPHERIC_TEMPERATURE_C", "15"))
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 60
    RATELIMIT_STORAGE_URI = "memory://"
    JSON_SORT_KEYS = False

