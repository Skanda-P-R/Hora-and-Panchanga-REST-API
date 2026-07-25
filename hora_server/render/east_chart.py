"""Traditional East Indian (Bengali/Odia 3x3 format) Kundali renderer."""

from __future__ import annotations

from hora_server.astrology.kundali import Kundali

from .chart_symbols import (
    ChartCell,
    ChartInfo,
    labels_by_rasi,
    render_grid_png,
    render_grid_svg,
)


EAST_LINES = (
    # Outer border
    (0, 0, 512, 0),
    (512, 0, 512, 512),
    (512, 512, 0, 512),
    (0, 512, 0, 0),
    # 3x3 Grid inner lines
    (171, 0, 171, 512),
    (341, 0, 341, 512),
    (0, 171, 512, 171),
    (0, 341, 512, 341),
    # Outer 4 corner cell diagonals only
    (0, 0, 171, 171),      # Top-left corner diagonal
    (512, 0, 341, 171),    # Top-right corner diagonal
    (0, 512, 171, 341),    # Bottom-left corner diagonal
    (512, 512, 341, 341),  # Bottom-right corner diagonal
)

EAST_INFO_BOX = (171, 171, 170, 170)

EAST_RASI_POSITIONS = {
    1: ((256, 24), (256, 85)),        # Mesha / Aries (Top Middle cell)
    2: ((135, 24), (114, 57)),        # Vrishabha / Taurus (Top-Left Upper triangle)
    3: ((24, 135), (57, 114)),        # Mithuna / Gemini (Top-Left Lower triangle)
    4: ((24, 195), (85, 256)),        # Karka / Cancer (Left Middle cell)
    5: ((24, 377), (57, 398)),        # Simha / Leo (Bottom-Left Upper triangle)
    6: ((135, 488), (114, 455)),      # Kanya / Virgo (Bottom-Left Lower triangle)
    7: ((256, 488), (256, 427)),      # Tula / Libra (Bottom Middle cell)
    8: ((377, 488), (398, 455)),      # Vrischika / Scorpio (Bottom-Right Lower triangle)
    9: ((488, 377), (455, 398)),      # Dhanus / Sagittarius (Bottom-Right Upper triangle)
    10: ((488, 195), (427, 256)),     # Makara / Capricorn (Right Middle cell)
    11: ((488, 135), (455, 114)),     # Kumbha / Aquarius (Top-Right Lower triangle)
    12: ((377, 24), (398, 57)),       # Meena / Pisces (Top-Right Upper triangle)
}


def _cells(kundali: Kundali, language: str = "en") -> tuple[ChartCell, ...]:
    labels = labels_by_rasi(kundali, language)
    return tuple(
        ChartCell(
            row=0,
            column=0,
            top_label=str(((rasi - kundali.lagna.number) % 12) + 1),
            labels=labels[rasi],
            top_label_pos=top_pos,
            center_pos=center_pos,
        )
        for rasi, (top_pos, center_pos) in EAST_RASI_POSITIONS.items()
    )


def render_svg(
    kundali: Kundali,
    chart_info: ChartInfo | None = None,
    language: str = "en",
) -> str:
    return render_grid_svg(_cells(kundali, language), chart_info, lines=EAST_LINES, info_box_rect=EAST_INFO_BOX)


def render_png(
    kundali: Kundali,
    chart_info: ChartInfo | None = None,
    language: str = "en",
) -> bytes:
    return render_grid_png(_cells(kundali, language), chart_info, language, lines=EAST_LINES, info_box_rect=EAST_INFO_BOX)
