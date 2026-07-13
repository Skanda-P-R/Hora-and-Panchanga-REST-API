"""Simple house-oriented Kundali renderer for east style."""

from __future__ import annotations

from hora_server.astrology.kundali import Kundali

from .chart_symbols import (
    ChartCell,
    ChartInfo,
    labels_by_house,
    render_grid_svg,
    render_grid_png,
)


EAST_HOUSE_CELLS = {
    1: (1, 0),
    2: (0, 0),
    3: (0, 1),
    4: (0, 2),
    5: (0, 3),
    6: (1, 3),
    7: (2, 3),
    8: (3, 3),
    9: (3, 2),
    10: (3, 1),
    11: (3, 0),
    12: (2, 0),
}


def _cells(kundali: Kundali, language: str = "en") -> tuple[ChartCell, ...]:
    labels = labels_by_house(kundali, language)
    return tuple(
        ChartCell(
            row=row,
            column=column,
            top_label=str(house),
            labels=labels[house],
        )
        for house, (row, column) in EAST_HOUSE_CELLS.items()
    )


def render_svg(
    kundali: Kundali,
    chart_info: ChartInfo | None = None,
    language: str = "en",
) -> str:
    return render_grid_svg(_cells(kundali, language), chart_info)


def render_png(
    kundali: Kundali,
    chart_info: ChartInfo | None = None,
    language: str = "en",
) -> bytes:
    return render_grid_png(_cells(kundali, language), chart_info, language)
