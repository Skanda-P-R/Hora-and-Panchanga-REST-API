from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from hora_server.astronomy.sunrise import SolarDay
from hora_server.astrology.muhurta import calculate_muhurta


def _eight_hour_day(local_date: date) -> SolarDay:
    timezone = ZoneInfo("UTC")
    sunrise = datetime(local_date.year, local_date.month, local_date.day, 8, tzinfo=timezone)
    sunset = sunrise + timedelta(hours=8)
    return SolarDay(local_date, sunrise, sunset, sunrise + timedelta(days=1))


def test_all_weekday_kalam_segment_tables():
    expected_rahu = (2, 7, 5, 6, 4, 3, 8)
    expected_gulika = (6, 5, 4, 3, 2, 1, 7)
    expected_yamaganda = (4, 3, 2, 1, 7, 6, 5)
    monday = date(2026, 7, 6)
    for weekday in range(7):
        solar_day = _eight_hour_day(monday + timedelta(days=weekday))
        result = calculate_muhurta(solar_day)
        assert result["rahu_kalam"].segment == expected_rahu[weekday]
        assert result["gulika"].segment == expected_gulika[weekday]
        assert result["yamaganda"].segment == expected_yamaganda[weekday]
        for key in ("rahu_kalam", "gulika", "yamaganda"):
            assert (result[key].end - result[key].start) == timedelta(hours=1)


def test_abhijit_is_eighth_of_fifteen_daylight_muhurtas():
    result = calculate_muhurta(_eight_hour_day(date(2026, 7, 6)))
    abhijit = result["abhijit"]

    assert abhijit.start == datetime(2026, 7, 6, 11, 44, tzinfo=ZoneInfo("UTC"))
    assert abhijit.end == datetime(2026, 7, 6, 12, 16, tzinfo=ZoneInfo("UTC"))
    assert abhijit.traditionally_auspicious is True


def test_wednesday_abhijit_is_returned_with_caveat():
    result = calculate_muhurta(_eight_hour_day(date(2026, 7, 8)))
    assert result["abhijit"].traditionally_auspicious is False
    assert "Wednesday" in result["abhijit"].note
