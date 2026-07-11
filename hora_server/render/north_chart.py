"""Simple house-oriented Kundali renderer for north style."""

from __future__ import annotations

from hora_server.astrology.kundali import Kundali

from .chart_symbols import ChartCell, labels_by_house, render_grid_png, render_grid_svg


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


def _cells(kundali: Kundali) -> tuple[ChartCell, ...]:
    labels = labels_by_house(kundali)
    return tuple(
        ChartCell(
            row=row,
            column=column,
            top_label=str(house),
            labels=labels[house],
        )
        for house, (row, column) in NORTH_HOUSE_CELLS.items()
    )


def render_svg(kundali: Kundali) -> str:
    return render_grid_svg(_cells(kundali))


def render_png(kundali: Kundali) -> bytes:
    return render_grid_png(_cells(kundali))
