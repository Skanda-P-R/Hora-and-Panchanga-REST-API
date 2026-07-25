"""South Indian static-rasi Kundali renderer."""

from __future__ import annotations

from hora_server.astrology.kundali import Kundali

from .chart_symbols import (
    ChartCell,
    ChartInfo,
    labels_by_rasi,
    render_grid_png,
    render_grid_svg,
)


SOUTH_RASI_CELLS = {
    12: (0, 0),
    1: (0, 1),
    2: (0, 2),
    3: (0, 3),
    11: (1, 0),
    4: (1, 3),
    10: (2, 0),
    5: (2, 3),
    9: (3, 0),
    8: (3, 1),
    7: (3, 2),
    6: (3, 3),
}


def _cells(kundali: Kundali, language: str = "en") -> tuple[ChartCell, ...]:
    labels = labels_by_rasi(kundali, language)
    return tuple(
        ChartCell(
            row=row,
            column=column,
            top_label=str(((rasi - kundali.lagna.number) % 12) + 1),
            labels=labels[rasi],
        )
        for rasi, (row, column) in SOUTH_RASI_CELLS.items()
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
