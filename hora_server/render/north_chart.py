"""Simple house-oriented Kundali renderer for north style."""

from __future__ import annotations

from hora_server.astrology.kundali import Kundali

from .chart_symbols import (
    ChartCell,
    ChartInfo,
    labels_by_house,
    render_grid_svg,
    render_grid_png,
)


NORTH_HOUSE_CELLS = {
    1: (0, 1),
    2: (0, 0),
    3: (1, 0),
    4: (2, 0),
    5: (3, 0),
    6: (3, 1),
    7: (3, 2),
    8: (3, 3),
    9: (2, 3),
    10: (1, 3),
    11: (0, 3),
    12: (0, 2),
}


def _cells(kundali: Kundali, language: str = "en") -> tuple[ChartCell, ...]:
    labels = labels_by_house(kundali, language)
    return tuple(
        ChartCell(
            row=row,
            column=column,
            top_label=str(kundali.houses[house - 1].rasi_number),
            labels=labels[house],
        )
        for house, (row, column) in NORTH_HOUSE_CELLS.items()
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
