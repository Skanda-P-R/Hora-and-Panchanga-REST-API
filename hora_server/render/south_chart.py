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
    1: (0, 1),   # Mesha / Aries (Row 0, Col 1)
    2: (0, 2),   # Vrishabha / Taurus (Row 0, Col 2)
    3: (0, 3),   # Mithuna / Gemini (Row 0, Col 3)
    4: (1, 3),   # Karka / Cancer (Row 1, Col 3)
    5: (2, 3),   # Simha / Leo (Row 2, Col 3)
    6: (3, 3),   # Kanya / Virgo (Row 3, Col 3)
    7: (3, 2),   # Tula / Libra (Row 3, Col 2)
    8: (3, 1),   # Vrischika / Scorpio (Row 3, Col 1)
    9: (3, 0),   # Dhanus / Sagittarius (Row 3, Col 0)
    10: (2, 0),  # Makara / Capricorn (Row 2, Col 0)
    11: (1, 0),  # Kumbha / Aquarius (Row 1, Col 0)
    12: (0, 0),  # Meena / Pisces (Row 0, Col 0)
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
