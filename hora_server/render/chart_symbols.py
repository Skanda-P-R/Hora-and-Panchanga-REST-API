"""Shared chart rendering helpers."""

from __future__ import annotations

import binascii
import struct
import zlib
from dataclasses import dataclass
from html import escape

from hora_server.astrology.kundali import Kundali
from hora_server.utils.errors import ApiError


CHART_SIZE = 512
GRID_SIZE = 4
CELL_SIZE = CHART_SIZE // GRID_SIZE
CHART_STYLES = ("south", "north", "east")


@dataclass(frozen=True)
class ChartCell:
    row: int
    column: int
    top_label: str
    labels: tuple[str, ...]


@dataclass(frozen=True)
class ChartInfo:
    title: str
    date: str
    time: str
    location: str


def resolve_chart_style(value: str | None) -> str:
    style = (value or "south").strip().lower()
    if style not in CHART_STYLES:
        raise ApiError(
            "chart_style is not supported",
            code="invalid_parameter",
            details={
                "parameter": "chart_style",
                "value": value,
                "supported": list(CHART_STYLES),
            },
        )
    return style


def planet_label(symbol: str, retrograde: bool) -> str:
    return f"{symbol}(R)" if retrograde else symbol


def labels_by_rasi(kundali: Kundali) -> dict[int, tuple[str, ...]]:
    labels: dict[int, list[str]] = {number: [] for number in range(1, 13)}
    labels[kundali.lagna.number].append("As")
    for planet in kundali.planets:
        labels[planet.rasi_number].append(
            planet_label(planet.symbol, planet.retrograde)
        )
    return {number: tuple(values) for number, values in labels.items()}


def labels_by_house(kundali: Kundali) -> dict[int, tuple[str, ...]]:
    labels: dict[int, list[str]] = {number: [] for number in range(1, 13)}
    labels[1].append("As")
    for planet in kundali.planets:
        labels[planet.house].append(planet_label(planet.symbol, planet.retrograde))
    return {number: tuple(values) for number, values in labels.items()}


def _center_lines() -> tuple[tuple[int, int, int, int], ...]:
    return (
        (CELL_SIZE, CELL_SIZE, CELL_SIZE * 3, CELL_SIZE),
        (CELL_SIZE * 3, CELL_SIZE, CELL_SIZE * 3, CELL_SIZE * 3),
        (CELL_SIZE * 3, CELL_SIZE * 3, CELL_SIZE, CELL_SIZE * 3),
        (CELL_SIZE, CELL_SIZE * 3, CELL_SIZE, CELL_SIZE),
    )


def _grid_lines() -> tuple[tuple[int, int, int, int], ...]:
    lines: list[tuple[int, int, int, int]] = []
    for index in range(GRID_SIZE + 1):
        offset = index * CELL_SIZE
        if index == 2:
            lines.extend(
                (
                    (offset, 0, offset, CELL_SIZE),
                    (offset, CELL_SIZE * 3, offset, CHART_SIZE),
                    (0, offset, CELL_SIZE, offset),
                    (CELL_SIZE * 3, offset, CHART_SIZE, offset),
                )
            )
        else:
            lines.append((offset, 0, offset, CHART_SIZE))
            lines.append((0, offset, CHART_SIZE, offset))
    lines.extend(_center_lines())
    return tuple(lines)


def render_grid_svg(
    cells: tuple[ChartCell, ...], chart_info: ChartInfo | None = None
) -> str:
    elements = [
        f'<rect x="0" y="0" width="{CHART_SIZE}" height="{CHART_SIZE}" fill="white"/>'
    ]
    for x1, y1, x2, y2 in _grid_lines():
        elements.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            'stroke="#111" stroke-width="2"/>'
        )

    for cell in cells:
        x = cell.column * CELL_SIZE
        y = cell.row * CELL_SIZE
        elements.append(
            f'<text x="{x + 8}" y="{y + 20}" font-family="Arial, sans-serif" '
            f'font-size="16" fill="#222">{escape(cell.top_label)}</text>'
        )
        if not cell.labels:
            continue
        line_height = 20
        start_y = y + (CELL_SIZE - (len(cell.labels) - 1) * line_height) / 2
        for index, label in enumerate(cell.labels):
            elements.append(
                f'<text x="{x + CELL_SIZE / 2}" y="{start_y + index * line_height}" '
                'font-family="Arial, sans-serif" font-size="18" fill="#111" '
                'text-anchor="middle" dominant-baseline="middle">'
                f"{escape(label)}</text>"
            )

    if chart_info:
        center_x = CHART_SIZE / 2
        text_lines = (
            (chart_info.title, 220, 20, "#111"),
            (chart_info.date, 252, 15, "#333"),
            (chart_info.time, 278, 15, "#333"),
            (chart_info.location, 304, 14, "#333"),
        )
        for text, y, size, color in text_lines:
            elements.append(
                f'<text x="{center_x}" y="{y}" font-family="Arial, sans-serif" '
                f'font-size="{size}" fill="{color}" text-anchor="middle" '
                f'dominant-baseline="middle">{escape(text)}</text>'
            )

    body = "".join(elements)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CHART_SIZE}" '
        f'height="{CHART_SIZE}" viewBox="0 0 {CHART_SIZE} {CHART_SIZE}">'
        f"{body}</svg>"
    )


_FONT: dict[str, tuple[str, ...]] = {
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "(": ("00110", "01100", "01000", "01000", "01000", "01100", "00110"),
    ")": ("01100", "00110", "00010", "00010", "00010", "00110", "01100"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    ",": ("00000", "00000", "00000", "00000", "00110", "00100", "01000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "11100"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
}


class SimpleCanvas:
    def __init__(self, width: int = CHART_SIZE, height: int = CHART_SIZE) -> None:
        self.width = width
        self.height = height
        self.pixels = bytearray([255] * width * height * 3)

    def _point(self, x: int, y: int, color: tuple[int, int, int], width: int) -> None:
        radius = max(0, width // 2)
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                self.set_pixel(x + dx, y + dy, color)

    def set_pixel(self, x: int, y: int, color: tuple[int, int, int]) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        index = (y * self.width + x) * 3
        self.pixels[index : index + 3] = bytes(color)

    def line(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        color: tuple[int, int, int] = (17, 17, 17),
        width: int = 2,
    ) -> None:
        dx = abs(x2 - x1)
        sx = 1 if x1 < x2 else -1
        dy = -abs(y2 - y1)
        sy = 1 if y1 < y2 else -1
        error = dx + dy
        while True:
            self._point(x1, y1, color, width)
            if x1 == x2 and y1 == y2:
                break
            doubled = 2 * error
            if doubled >= dy:
                error += dy
                x1 += sx
            if doubled <= dx:
                error += dx
                y1 += sy

    def text(
        self,
        text: str,
        x: int,
        y: int,
        scale: int = 3,
        color: tuple[int, int, int] = (17, 17, 17),
    ) -> None:
        cursor = x
        for character in text.upper():
            glyph = _FONT.get(character, _FONT[" "])
            for row, pattern in enumerate(glyph):
                for column, bit in enumerate(pattern):
                    if bit == "1":
                        for yy in range(scale):
                            for xx in range(scale):
                                self.set_pixel(
                                    cursor + column * scale + xx,
                                    y + row * scale + yy,
                                    color,
                                )
            cursor += (len(glyph[0]) + 1) * scale

    @staticmethod
    def text_size(text: str, scale: int = 3) -> tuple[int, int]:
        if not text:
            return 0, 7 * scale
        return ((5 + 1) * scale * len(text) - scale, 7 * scale)

    def to_png(self) -> bytes:
        rows = bytearray()
        row_width = self.width * 3
        for y in range(self.height):
            rows.append(0)
            start = y * row_width
            rows.extend(self.pixels[start : start + row_width])
        payload = zlib.compress(bytes(rows))

        def chunk(kind: bytes, data: bytes) -> bytes:
            checksum = binascii.crc32(kind + data) & 0xFFFFFFFF
            return (
                struct.pack(">I", len(data))
                + kind
                + data
                + struct.pack(">I", checksum)
            )

        header = struct.pack(">IIBBBBB", self.width, self.height, 8, 2, 0, 0, 0)
        return (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", header)
            + chunk(b"IDAT", payload)
            + chunk(b"IEND", b"")
        )


def _center_text(canvas: SimpleCanvas, chart_info: ChartInfo) -> None:
    lines = (
        (chart_info.title, 190, 2),
        (chart_info.date, 230, 2),
        (chart_info.time, 260, 2),
        (chart_info.location, 290, 1),
    )
    for text, y, scale in lines:
        text_width, _ = canvas.text_size(text, scale=scale)
        canvas.text(text, (CHART_SIZE - text_width) // 2, y, scale=scale)


def render_grid_png(
    cells: tuple[ChartCell, ...], chart_info: ChartInfo | None = None
) -> bytes:
    canvas = SimpleCanvas()
    for x1, y1, x2, y2 in _grid_lines():
        canvas.line(x1, y1, x2, y2)

    for cell in cells:
        x = cell.column * CELL_SIZE
        y = cell.row * CELL_SIZE
        canvas.text(cell.top_label, x + 8, y + 8, scale=2, color=(34, 34, 34))
        if not cell.labels:
            continue
        scale = 3 if len(cell.labels) <= 4 else 2
        line_height = 8 * scale + 4
        total_height = len(cell.labels) * line_height
        start_y = y + max(32, (CELL_SIZE - total_height) // 2 + 8)
        for index, label in enumerate(cell.labels):
            text_width, _ = canvas.text_size(label, scale=scale)
            canvas.text(
                label,
                x + (CELL_SIZE - text_width) // 2,
                start_y + index * line_height,
                scale=scale,
            )
    if chart_info:
        _center_text(canvas, chart_info)
    return canvas.to_png()
