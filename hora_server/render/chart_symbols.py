"""Shared chart rendering helpers."""

from __future__ import annotations

import binascii
import io
import math
import os
import struct
import zlib
from dataclasses import dataclass
from html import escape
from pathlib import Path

import freetype
import uharfbuzz as hb
from PIL import Image, ImageDraw, ImageFont

from hora_server.astrology.kundali import Kundali
from hora_server.utils.errors import ApiError


CHART_SIZE = 512
GRID_SIZE = 4
CELL_SIZE = CHART_SIZE // GRID_SIZE
CHART_STYLES = ("south", "north", "east")
CHART_LANGUAGES = ("en", "kan")
SYMBOL_MAP = {
    "Su": "ಸೂರ್ಯ",
    "Mo": "ಚಂದ್ರ",
    "Ma": "ಕುಜ",
    "Me": "ಬುಧ",
    "Ju": "ಗುರು",
    "Ve": "ಶುಕ್ರ",
    "Sa": "ಶನಿ",
    "Ra": "ರಾಹು",
    "Ke": "ಕೇತು",
    "AS": "ಲಗ್ನ",
}
KANNADA_TITLE = "ಗೋಚಾರ ಕುಂಡಲಿ"
SVG_FONT_FAMILY = "Nirmala UI, Tunga, Noto Sans Kannada, Arial, sans-serif"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FONT_DIR = PROJECT_ROOT / "fonts"
UNICODE_FONT_CANDIDATES = (
    FONT_DIR / "Nirmala.ttf",
    FONT_DIR / "NirmalaB.ttf",
)


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


def resolve_chart_language(value: str | None) -> str:
    language = (value or "en").strip().lower()
    if language not in CHART_LANGUAGES:
        raise ApiError(
            "lang is not supported",
            code="invalid_parameter",
            details={
                "parameter": "lang",
                "value": value,
                "supported": list(CHART_LANGUAGES),
            },
        )
    return language


def localized_symbol(symbol: str, language: str) -> str:
    if language == "kan":
        return SYMBOL_MAP[symbol]
    return symbol


def localized_title(language: str) -> str:
    return KANNADA_TITLE if language == "kan" else "Transit Kundali"


def planet_label(
    symbol: str, retrograde: bool, language: str = "en"
) -> str:
    label = localized_symbol(symbol, language)
    return f"{label}(R)" if retrograde else label


def degree_minute_text(degree: float) -> str:
    whole_degrees = math.floor(degree)
    minutes = int((degree - whole_degrees) * 60)

    return f"{whole_degrees}\N{DEGREE SIGN}{minutes:02d}'"


def ascendant_label(kundali: Kundali, language: str = "en") -> str:
    return (
        f"{localized_symbol('AS', language)}\n"
        f"{degree_minute_text(kundali.lagna.degree_in_rasi)}"
    )


def labels_by_rasi(
    kundali: Kundali, language: str = "en"
) -> dict[int, tuple[str, ...]]:
    labels: dict[int, list[str]] = {number: [] for number in range(1, 13)}
    labels[kundali.lagna.number].append(ascendant_label(kundali, language))
    for planet in kundali.planets:
        labels[planet.rasi_number].append(
            planet_label(planet.symbol, planet.retrograde, language)
        )
    return {number: tuple(values) for number, values in labels.items()}


def labels_by_house(
    kundali: Kundali, language: str = "en"
) -> dict[int, tuple[str, ...]]:
    labels: dict[int, list[str]] = {number: [] for number in range(1, 13)}
    labels[1].append(ascendant_label(kundali, language))
    for planet in kundali.planets:
        labels[planet.house].append(
            planet_label(planet.symbol, planet.retrograde, language)
        )
    return {number: tuple(values) for number, values in labels.items()}


def _display_lines(labels: tuple[str, ...]) -> tuple[str, ...]:
    lines: list[str] = []
    for label in labels:
        if lines:
            lines.append("")
        lines.extend(label.splitlines())
    return tuple(lines)


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
            f'<text x="{x + 8}" y="{y + 20}" font-family="{SVG_FONT_FAMILY}" '
            f'font-size="16" fill="#222">{escape(cell.top_label, quote=False)}</text>'
        )
        if not cell.labels:
            continue
        display_lines = _display_lines(cell.labels)
        line_height = 19
        start_y = y + (CELL_SIZE - (len(display_lines) - 1) * line_height) / 2
        for index, label in enumerate(display_lines):
            if not label:
                continue
            elements.append(
                f'<text x="{x + CELL_SIZE / 2}" y="{start_y + index * line_height}" '
                f'font-family="{SVG_FONT_FAMILY}" font-size="18" fill="#111" '
                'text-anchor="middle" dominant-baseline="middle">'
                f"{escape(label, quote=False)}</text>"
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
                f'<text x="{center_x}" y="{y}" font-family="{SVG_FONT_FAMILY}" '
                f'font-size="{size}" fill="{color}" text-anchor="middle" '
                f'dominant-baseline="middle">{escape(text, quote=False)}</text>'
            )

    body = "".join(elements)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CHART_SIZE}" '
        f'height="{CHART_SIZE}" viewBox="0 0 {CHART_SIZE} {CHART_SIZE}">'
        f"{body}</svg>"
    )


_FONT: dict[str, tuple[str, ...]] = {
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "'": ("01100", "01100", "00100", "01000", "00000", "00000", "00000"),
    "(": ("00110", "01100", "01000", "01000", "01000", "01100", "00110"),
    ")": ("01100", "00110", "00010", "00010", "00010", "00110", "01100"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    ",": ("00000", "00000", "00000", "00000", "00110", "00100", "01000"),
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "\N{DEGREE SIGN}": (
        "01100",
        "10010",
        "10010",
        "01100",
        "00000",
        "00000",
        "00000",
    ),
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


def _unicode_font_path() -> Path | None:
    configured = os.getenv("KUNDALI_FONT_PATH")
    candidates = (configured, *UNICODE_FONT_CANDIDATES) if configured else UNICODE_FONT_CANDIDATES
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    return None


def _unicode_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_path = _unicode_font_path()
    if font_path:
        return ImageFont.truetype(font_path, size=size)
    return ImageFont.load_default()


class ShapedTextRenderer:
    def __init__(self, font_path: Path, size: int) -> None:
        self.face = freetype.Face(str(font_path))
        self.face.set_pixel_sizes(0, size)
        font_data = font_path.read_bytes()
        self.hb_face = hb.Face(font_data)
        self.hb_font = hb.Font(self.hb_face)
        self.hb_font.scale = (size * 64, size * 64)
        hb.ot_font_set_funcs(self.hb_font)

    def _glyphs(self, text: str):
        buffer = hb.Buffer()
        buffer.add_str(text)
        buffer.guess_segment_properties()
        hb.shape(self.hb_font, buffer, {"kern": True, "liga": True})
        return zip(buffer.glyph_infos, buffer.glyph_positions)

    def bounds(self, text: str) -> tuple[float, float, float, float]:
        pen_x = 0.0
        pen_y = 0.0
        bounds: list[tuple[float, float, float, float]] = []
        for info, position in self._glyphs(text):
            self.face.load_glyph(info.codepoint, freetype.FT_LOAD_RENDER)
            glyph = self.face.glyph
            bitmap = glyph.bitmap
            x = pen_x + position.x_offset / 64 + glyph.bitmap_left
            y = pen_y - position.y_offset / 64 - glyph.bitmap_top
            bounds.append((x, y, x + bitmap.width, y + bitmap.rows))
            pen_x += position.x_advance / 64
            pen_y -= position.y_advance / 64
        if not bounds:
            return (0, 0, 0, 0)
        return (
            min(item[0] for item in bounds),
            min(item[1] for item in bounds),
            max(item[2] for item in bounds),
            max(item[3] for item in bounds),
        )

    def draw(
        self,
        image: Image.Image,
        text: str,
        x: float,
        baseline_y: float,
        fill: tuple[int, int, int] = (17, 17, 17),
    ) -> None:
        pen_x = x
        pen_y = baseline_y
        pixels = image.load()
        for info, position in self._glyphs(text):
            self.face.load_glyph(info.codepoint, freetype.FT_LOAD_RENDER)
            glyph = self.face.glyph
            bitmap = glyph.bitmap
            left = round(pen_x + position.x_offset / 64 + glyph.bitmap_left)
            top = round(pen_y - position.y_offset / 64 - glyph.bitmap_top)
            for row in range(bitmap.rows):
                for column in range(bitmap.width):
                    alpha = bitmap.buffer[row * bitmap.pitch + column]
                    if not alpha:
                        continue
                    target_x = left + column
                    target_y = top + row
                    if not (0 <= target_x < image.width and 0 <= target_y < image.height):
                        continue
                    existing = pixels[target_x, target_y]
                    ratio = alpha / 255
                    pixels[target_x, target_y] = tuple(
                        round(existing[index] * (1 - ratio) + fill[index] * ratio)
                        for index in range(3)
                    )
            pen_x += position.x_advance / 64
            pen_y -= position.y_advance / 64


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    center_x: float,
    y: float,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int] = (17, 17, 17),
) -> None:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    draw.text((center_x - (right - left) / 2, y - (bottom - top) / 2), text, font=font, fill=fill)


def _draw_centered_shaped_text(
    image: Image.Image,
    renderer: ShapedTextRenderer,
    text: str,
    center_x: float,
    center_y: float,
    fill: tuple[int, int, int] = (17, 17, 17),
) -> None:
    left, top, right, bottom = renderer.bounds(text)
    origin_x = center_x - (right - left) / 2 - left
    baseline_y = center_y - (bottom - top) / 2 - top
    renderer.draw(image, text, origin_x, baseline_y, fill)


def _render_unicode_grid_png(
    cells: tuple[ChartCell, ...], chart_info: ChartInfo | None = None
) -> bytes:
    image = Image.new("RGB", (CHART_SIZE, CHART_SIZE), "white")
    draw = ImageDraw.Draw(image)
    for line in _grid_lines():
        draw.line(line, fill=(17, 17, 17), width=2)

    font_path = _unicode_font_path()
    if not font_path:
        top_font = _unicode_font(16)
        label_font = _unicode_font(20)
        compact_label_font = _unicode_font(16)
        title_font = _unicode_font(20)
        detail_font = _unicode_font(15)
        location_font = _unicode_font(11)
    else:
        top_text = ShapedTextRenderer(font_path, 16)
        label_text = ShapedTextRenderer(font_path, 20)
        compact_label_text = ShapedTextRenderer(font_path, 16)
        title_text = ShapedTextRenderer(font_path, 20)
        detail_text = ShapedTextRenderer(font_path, 15)
        location_text = ShapedTextRenderer(font_path, 11)

    for cell in cells:
        x = cell.column * CELL_SIZE
        y = cell.row * CELL_SIZE
        if font_path:
            top_text.draw(image, cell.top_label, x + 8, y + 20, (34, 34, 34))
        else:
            draw.text((x + 8, y + 5), cell.top_label, font=top_font, fill=(34, 34, 34))
        display_lines = _display_lines(cell.labels)
        if not display_lines:
            continue
        if font_path:
            shaped_font = (
                label_text if len(display_lines) <= 4 else compact_label_text
            )
        else:
            font = label_font if len(display_lines) <= 4 else compact_label_font
        line_height = 24 if len(display_lines) <= 4 else 20
        total_height = len(display_lines) * line_height
        start_y = y + max(28, (CELL_SIZE - total_height) / 2 + line_height / 2)
        for index, label in enumerate(display_lines):
            if not label:
                continue
            center_y = start_y + index * line_height
            if font_path:
                _draw_centered_shaped_text(
                    image, shaped_font, label, x + CELL_SIZE / 2, center_y
                )
            else:
                _draw_centered_text(draw, label, x + CELL_SIZE / 2, center_y, font)

    if chart_info:
        if font_path:
            center_lines = (
                (chart_info.title, 198, title_text, (17, 17, 17)),
                (chart_info.date, 236, detail_text, (51, 51, 51)),
                (chart_info.time, 264, detail_text, (51, 51, 51)),
                (chart_info.location, 296, location_text, (51, 51, 51)),
            )
            for text, y, renderer, color in center_lines:
                _draw_centered_shaped_text(image, renderer, text, CHART_SIZE / 2, y, color)
        else:
            for text, y, font, color in (
                (chart_info.title, 198, title_font, (17, 17, 17)),
                (chart_info.date, 236, detail_font, (51, 51, 51)),
                (chart_info.time, 264, detail_font, (51, 51, 51)),
                (chart_info.location, 296, location_font, (51, 51, 51)),
            ):
                _draw_centered_text(draw, text, CHART_SIZE / 2, y, font, color)

    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def render_grid_png(
    cells: tuple[ChartCell, ...],
    chart_info: ChartInfo | None = None,
    language: str = "en",
) -> bytes:
    if language != "en":
        return _render_unicode_grid_png(cells, chart_info)

    canvas = SimpleCanvas()
    for x1, y1, x2, y2 in _grid_lines():
        canvas.line(x1, y1, x2, y2)

    for cell in cells:
        x = cell.column * CELL_SIZE
        y = cell.row * CELL_SIZE
        canvas.text(cell.top_label, x + 8, y + 8, scale=2, color=(34, 34, 34))
        if not cell.labels:
            continue
        display_lines = _display_lines(cell.labels)
        scale = 3 if len(display_lines) <= 4 else 2
        line_height = 8 * scale + 4
        total_height = len(display_lines) * line_height
        start_y = y + max(32, (CELL_SIZE - total_height) // 2 + 8)
        for index, label in enumerate(display_lines):
            if not label:
                continue
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
