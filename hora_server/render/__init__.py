"""Chart rendering dispatch."""

from __future__ import annotations

from hora_server.astrology.kundali import Kundali

from . import east_chart, north_chart, south_chart
from .chart_symbols import resolve_chart_style


def render_kundali_svg(kundali: Kundali, chart_style: str = "south") -> str:
    style = resolve_chart_style(chart_style)
    renderer = {
        "south": south_chart,
        "north": north_chart,
        "east": east_chart,
    }[style]
    return renderer.render_svg(kundali)


def render_kundali_png(kundali: Kundali, chart_style: str = "south") -> bytes:
    style = resolve_chart_style(chart_style)
    renderer = {
        "south": south_chart,
        "north": north_chart,
        "east": east_chart,
    }[style]
    return renderer.render_png(kundali)


__all__ = ["render_kundali_png", "render_kundali_svg", "resolve_chart_style"]
