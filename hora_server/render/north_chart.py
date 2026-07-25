"""Traditional North Indian (Diamond format) Kundali renderer."""

from __future__ import annotations

from hora_server.astrology.kundali import Kundali

from .chart_symbols import (
    ChartCell,
    ChartInfo,
    labels_by_house,
    render_grid_png,
    render_grid_svg,
)


NORTH_LINES = (
    (0, 0, 512, 0),
    (512, 0, 512, 512),
    (512, 512, 0, 512),
    (0, 512, 0, 0),
    (0, 0, 512, 512),
    (512, 0, 0, 512),
    (256, 0, 512, 256),
    (512, 256, 256, 512),
    (256, 512, 0, 256),
    (0, 256, 256, 0),
)

NORTH_INFO_BOX = (171, 196, 170, 120)

NORTH_HOUSE_POSITIONS = {
    1: ((256, 28), (256, 128)),     # House 1 / Lagna (Top Center diamond)
    2: ((170, 24), (110, 60)),      # House 2 (Top-Left Corner triangle)
    3: ((24, 170), (60, 110)),      # House 3 (Upper-Left Side triangle)
    4: ((28, 256), (115, 256)),     # House 4 (Left Center diamond)
    5: ((24, 342), (60, 402)),      # House 5 (Lower-Left Side triangle)
    6: ((170, 488), (110, 452)),    # House 6 (Bottom-Left Corner triangle)
    7: ((256, 484), (256, 384)),    # House 7 (Bottom Center diamond)
    8: ((342, 488), (402, 452)),    # House 8 (Bottom-Right Corner triangle)
    9: ((488, 342), (452, 402)),    # House 9 (Lower-Right Side triangle)
    10: ((484, 256), (397, 256)),   # House 10 (Right Center diamond)
    11: ((488, 170), (452, 110)),   # House 11 (Upper-Right Side triangle)
    12: ((342, 24), (402, 60)),     # House 12 (Top-Right Corner triangle)
}


def _cells(kundali: Kundali, language: str = "en") -> tuple[ChartCell, ...]:
    labels = labels_by_house(kundali, language)
    return tuple(
        ChartCell(
            row=0,
            column=0,
            top_label=str(kundali.houses[house - 1].rasi_number),
            labels=labels[house],
            top_label_pos=top_pos,
            center_pos=center_pos,
        )
        for house, (top_pos, center_pos) in NORTH_HOUSE_POSITIONS.items()
    )


def render_svg(
    kundali: Kundali,
    chart_info: ChartInfo | None = None,
    language: str = "en",
) -> str:
    return render_grid_svg(_cells(kundali, language), chart_info, lines=NORTH_LINES, info_box_rect=NORTH_INFO_BOX)


def render_png(
    kundali: Kundali,
    chart_info: ChartInfo | None = None,
    language: str = "en",
) -> bytes:
    return render_grid_png(_cells(kundali, language), chart_info, language, lines=NORTH_LINES, info_box_rect=NORTH_INFO_BOX)
