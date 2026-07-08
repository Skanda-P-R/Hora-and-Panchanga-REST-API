from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from hora_server.astronomy.sunrise import SolarCalculator
from hora_server.utils.errors import ApiError


class OrderedFakeEngine:
    """Returns a sunrise, then an invalid pre-sunrise sunset and transit."""

    def __init__(self):
        self.events = iter(
            (
                datetime(2026, 5, 1, 2, tzinfo=UTC),
                datetime(2026, 5, 1, 1, tzinfo=UTC),
                datetime(2026, 5, 1, 8, tzinfo=UTC),
                datetime(2026, 5, 2, 2, tzinfo=UTC),
            )
        )

    def rise_or_set(self, *args, **kwargs):
        return next(self.events)


def test_reversed_solar_cycle_is_rejected_instead_of_creating_negative_hours():
    calculator = SolarCalculator(OrderedFakeEngine())
    with pytest.raises(ApiError) as error:
        calculator.for_date(
            date(2026, 5, 1),
            66.0,
            25.0,
            ZoneInfo("UTC"),
        )
    assert error.value.code == "solar_event_unavailable"

