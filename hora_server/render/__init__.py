"""Chart rendering dispatch."""

from __future__ import annotations

from hora_server.astrology.kundali import Kundali

from . import east_chart, north_chart, south_chart
from .chart_symbols import ChartInfo, resolve_chart_language, resolve_chart_style


def render_kundali_svg(
    kundali: Kundali,
    chart_style: str = "south",
    chart_info: ChartInfo | None = None,
    language: str = "en",
) -> str:
    style = resolve_chart_style(chart_style)
    language = resolve_chart_language(language)
    renderer = {
        "south": south_chart,
        "north": north_chart,
        "east": east_chart,
    }[style]
    return renderer.render_svg(kundali, chart_info, language)


def render_kundali_png(
    kundali: Kundali,
    chart_style: str = "south",
    chart_info: ChartInfo | None = None,
    language: str = "en",
) -> bytes:
    style = resolve_chart_style(chart_style)
    language = resolve_chart_language(language)
    renderer = {
        "south": south_chart,
        "north": north_chart,
        "east": east_chart,
    }[style]
    return renderer.render_png(kundali, chart_info, language)


__all__ = [
    "ChartInfo",
    "render_kundali_png",
    "render_kundali_svg",
    "resolve_chart_language",
    "resolve_chart_style",
]
