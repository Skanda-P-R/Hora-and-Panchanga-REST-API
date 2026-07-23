"""Timezone-safe datetime parsing and presentation helpers."""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from .errors import ApiError


def _localize_naive(value: datetime, timezone: ZoneInfo) -> datetime:
    local = value.replace(tzinfo=timezone, fold=0)
    try:
        round_trip = local.astimezone(UTC).astimezone(timezone).replace(tzinfo=None)
    except (OverflowError, OSError) as exc:
        raise ApiError(
            "datetime is outside the representable timezone range",
            code="datetime_out_of_range",
            status_code=422,
            details={"parameter": "datetime"},
        ) from exc
    if round_trip != value:
        raise ApiError(
            "datetime is a nonexistent local time in the selected timezone",
            code="nonexistent_local_datetime",
            details={"parameter": "datetime", "timezone": timezone.key},
        )

    alternate = value.replace(tzinfo=timezone, fold=1)
    if alternate.utcoffset() != local.utcoffset():
        raise ApiError(
            "datetime is ambiguous in the selected timezone; include a UTC offset",
            code="ambiguous_local_datetime",
            details={"parameter": "datetime", "timezone": timezone.key},
        )
    return local


def parse_iso_datetime(value: str | None, timezone: ZoneInfo) -> datetime:
    if value is None or not value.strip():
        return datetime.now(UTC).astimezone(timezone)

    normalized = value.strip()
    if normalized.endswith(("Z", "z")):
        normalized = f"{normalized[:-1]}+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ApiError(
            "datetime must be a valid ISO-8601 date or timestamp",
            code="invalid_datetime",
            details={"parameter": "datetime"},
        ) from exc

    if parsed.tzinfo is not None:
        try:
            return parsed.astimezone(timezone)
        except (OverflowError, OSError) as exc:
            raise ApiError(
                "datetime is outside the representable timezone range",
                code="datetime_out_of_range",
                status_code=422,
                details={"parameter": "datetime"},
            ) from exc

    # A date-only request represents local noon, which is stable across DST
    # changes and is the most useful instant for a daily almanac query.
    if "T" not in normalized and " " not in normalized:
        try:
            parsed_date = date.fromisoformat(normalized)
        except ValueError as exc:
            raise ApiError(
                "datetime must be a valid ISO-8601 date or timestamp",
                code="invalid_datetime",
                details={"parameter": "datetime"},
            ) from exc
        return _localize_naive(
            datetime.combine(parsed_date, datetime.min.time()) + timedelta(hours=12),
            timezone,
        )

    # An unqualified time during a fall-back fold maps to two instants. The
    # shared localizer validates gaps, folds, and representable range.
    return _localize_naive(parsed, timezone)


def isoformat(value: datetime) -> str:
    return value.isoformat(timespec="microseconds")


def time_text(value: datetime) -> str:
    return value.strftime("%H:%M")


def interval_text(start: datetime, end: datetime) -> str:
    return f"{time_text(start)}-{time_text(end)}"


def remaining_text(seconds: float) -> str:
    minutes = max(0, math.ceil(seconds / 60))
    return f"{minutes} min"


def duration_seconds(start: datetime, end: datetime) -> float:
    # Subtracting two datetimes with the same ZoneInfo object uses wall time;
    # UTC conversion preserves elapsed time through DST changes.
    return (end.astimezone(UTC) - start.astimezone(UTC)).total_seconds()


def add_elapsed(start: datetime, seconds: float) -> datetime:
    return (start.astimezone(UTC) + timedelta(seconds=seconds)).astimezone(
        start.tzinfo
    )
