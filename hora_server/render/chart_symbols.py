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
)


@dataclass(frozen=True)
class ChartCell:
    row: int
    column: int
    top_label: str
    labels: tuple[str, ...]
    top_label_pos: tuple[float, float] | None = None
    center_pos: tuple[float, float] | None = None


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
    cells: tuple[ChartCell, ...],
    chart_info: ChartInfo | None = None,
    lines: tuple[tuple[int, int, int, int], ...] | None = None,
    info_box_rect: tuple[int, int, int, int] | None = None,
) -> str:
    elements = [
        f'<rect x="0" y="0" width="{CHART_SIZE}" height="{CHART_SIZE}" fill="white"/>'
    ]
    grid_lines = lines if lines is not None else _grid_lines()
    for x1, y1, x2, y2 in grid_lines:
        elements.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            'stroke="#111" stroke-width="2"/>'
        )

    if info_box_rect and info_box_rect != (171, 171, 170, 170):
        bx, by, bw, bh = info_box_rect
        elements.append(
            f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" '
            'fill="white" stroke="#111" stroke-width="1.5"/>'
        )

    for cell in cells:
        if cell.top_label_pos:
            top_x, top_y = cell.top_label_pos
            anchor = 'text-anchor="middle" '
        else:
            top_x = cell.column * CELL_SIZE + 8
            top_y = cell.row * CELL_SIZE + 20
            anchor = ""
        elements.append(
            f'<text x="{top_x}" y="{top_y}" font-family="{SVG_FONT_FAMILY}" '
            f'font-size="16" fill="#222" {anchor}>{escape(cell.top_label, quote=False)}</text>'
        )
        if not cell.labels:
            continue
        display_lines = _display_lines(cell.labels)
        font_size = 15 if len(display_lines) >= 3 else 18
        line_height = 16 if len(display_lines) >= 3 else 19
        if cell.center_pos:
            cx, cy = cell.center_pos
            start_y = cy - ((len(display_lines) - 1) * line_height) / 2
        else:
            cx = cell.column * CELL_SIZE + CELL_SIZE / 2
            y = cell.row * CELL_SIZE
            start_y = y + (CELL_SIZE - (len(display_lines) - 1) * line_height) / 2

        for index, label in enumerate(display_lines):
            if not label:
                continue
            elements.append(
                f'<text x="{cx}" y="{start_y + index * line_height}" '
                f'font-family="{SVG_FONT_FAMILY}" font-size="{font_size}" fill="#111" '
                'text-anchor="middle" dominant-baseline="middle">'
                f"{escape(label, quote=False)}</text>"
            )

    if chart_info:
        center_x = CHART_SIZE / 2
        title_parts = chart_info.title.split(" - ", 1) if " - " in chart_info.title else [chart_info.title]
        if info_box_rect:
            _, by, _, bh = info_box_rect
            box_cy = by + bh / 2
            curr_y = box_cy - 40 if len(title_parts) > 1 else box_cy - 30
        else:
            curr_y = 216 if len(title_parts) > 1 else 226

        for idx, t_text in enumerate(title_parts):
            t_size = 15 if (len(t_text) > 14 or len(title_parts) > 1) else 18
            elements.append(
                f'<text x="{center_x}" y="{curr_y}" font-family="{SVG_FONT_FAMILY}" '
                f'font-size="{t_size}" fill="#111" text-anchor="middle" '
                f'dominant-baseline="middle">{escape(t_text, quote=False)}</text>'
            )
            curr_y += 20 if len(title_parts) > 1 else 24

        curr_y += 4
        for text, size, color in (
            (chart_info.date, 13, "#333"),
            (chart_info.time, 13, "#333"),
            (chart_info.location, 10.5, "#333"),
        ):
            elements.append(
                f'<text x="{center_x}" y="{curr_y}" font-family="{SVG_FONT_FAMILY}" '
                f'font-size="{size}" fill="{color}" text-anchor="middle" '
                f'dominant-baseline="middle">{escape(text, quote=False)}</text>'
            )
            curr_y += 20 if text == chart_info.date else 18

    body = "".join(elements)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CHART_SIZE}" '
        f'height="{CHART_SIZE}" viewBox="0 0 {CHART_SIZE} {CHART_SIZE}">'
        f"{body}</svg>"
    )


ENGLISH_FONT_CANDIDATES = (
    FONT_DIR / "Nirmala.ttf",
)


def _english_font_path() -> Path | None:
    configured = os.getenv("KUNDALI_ENGLISH_FONT_PATH") or os.getenv("KUNDALI_FONT_PATH")
    candidates = (configured, *ENGLISH_FONT_CANDIDATES) if configured else ENGLISH_FONT_CANDIDATES
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    return None


def _english_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_path = _english_font_path()
    if font_path:
        return ImageFont.truetype(str(font_path), size=size)
    return ImageFont.load_default()


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
                    pixels[target_x, target_y] = (
                        round(existing[0] * (1 - ratio) + fill[0] * ratio),
                        round(existing[1] * (1 - ratio) + fill[1] * ratio),
                        round(existing[2] * (1 - ratio) + fill[2] * ratio),
                    )
            pen_x += position.x_advance / 64
            pen_y -= position.y_advance / 64


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    center_x: float,
    center_y: float,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int] = (17, 17, 17),
) -> None:
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    x = center_x - (right - left) / 2 - left
    y = center_y - (bottom - top) / 2 - top
    draw.text((x, y), text, font=font, fill=fill)


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


def _png_line(line: tuple[int, int, int, int], width: int = 2) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = line
    if x1 == CHART_SIZE and x2 == CHART_SIZE:
        x1 = x2 = CHART_SIZE - width
    if y1 == CHART_SIZE and y2 == CHART_SIZE:
        y1 = y2 = CHART_SIZE - width
    return (x1, y1, x2, y2)


def _render_unicode_grid_png(
    cells: tuple[ChartCell, ...],
    chart_info: ChartInfo | None = None,
    lines: tuple[tuple[int, int, int, int], ...] | None = None,
    info_box_rect: tuple[int, int, int, int] | None = None,
) -> bytes:
    image = Image.new("RGB", (CHART_SIZE, CHART_SIZE), "white")
    draw = ImageDraw.Draw(image)
    grid_lines = lines if lines is not None else _grid_lines()
    for line in grid_lines:
        draw.line(_png_line(line), fill=(17, 17, 17), width=2)

    if info_box_rect and info_box_rect != (171, 171, 170, 170):
        bx, by, bw, bh = info_box_rect
        draw.rectangle([bx, by, bx + bw, by + bh], fill=(255, 255, 255), outline=(17, 17, 17), width=1)

    font_path = _unicode_font_path()
    if not font_path:
        top_font = _unicode_font(16)
        label_font = _unicode_font(20)
        compact_label_font = _unicode_font(15)
    else:
        top_text = ShapedTextRenderer(font_path, 16)
        label_text = ShapedTextRenderer(font_path, 20)
        compact_label_text = ShapedTextRenderer(font_path, 15)

    for cell in cells:
        if cell.top_label_pos:
            top_x, top_y = cell.top_label_pos
            if font_path:
                _draw_centered_shaped_text(image, top_text, cell.top_label, top_x, top_y, (34, 34, 34))
            else:
                _draw_centered_text(draw, cell.top_label, top_x, top_y, top_font, (34, 34, 34))
        else:
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
            shaped_font = label_text if len(display_lines) < 3 else compact_label_text
        else:
            font = label_font if len(display_lines) < 3 else compact_label_font
        line_height = 24 if len(display_lines) < 3 else 18
        total_height = len(display_lines) * line_height

        if cell.center_pos:
            cx, cy = cell.center_pos
            start_y = cy - total_height / 2 + line_height / 2
        else:
            cx = cell.column * CELL_SIZE + CELL_SIZE / 2
            y = cell.row * CELL_SIZE
            start_y = y + max(28, (CELL_SIZE - total_height) / 2 + line_height / 2)

        for index, label in enumerate(display_lines):
            if not label:
                continue
            center_y = start_y + index * line_height
            if font_path:
                _draw_centered_shaped_text(image, shaped_font, label, cx, center_y)
            else:
                _draw_centered_text(draw, label, cx, center_y, font)

    if chart_info:
        title_parts = chart_info.title.split(" - ", 1) if " - " in chart_info.title else [chart_info.title]
        if info_box_rect:
            _, by, _, bh = info_box_rect
            box_cy = by + bh / 2
            curr_y = box_cy - 40 if len(title_parts) > 1 else box_cy - 30
        else:
            curr_y = 216 if len(title_parts) > 1 else 226

        for idx, t_text in enumerate(title_parts):
            t_size = 15 if (len(t_text) > 14 or len(title_parts) > 1) else 18
            if font_path:
                t_renderer = ShapedTextRenderer(font_path, t_size)
                _draw_centered_shaped_text(image, t_renderer, t_text, CHART_SIZE / 2, curr_y, (17, 17, 17))
            else:
                t_font = _unicode_font(t_size)
                _draw_centered_text(draw, t_text, CHART_SIZE / 2, curr_y, t_font, (17, 17, 17))
            curr_y += 22 if len(title_parts) > 1 else 26

        curr_y += 2
        for text, size, color in (
            (chart_info.date, 13, (51, 51, 51)),
            (chart_info.time, 13, (51, 51, 51)),
            (chart_info.location, 10, (51, 51, 51)),
        ):
            if font_path:
                d_renderer = ShapedTextRenderer(font_path, size)
                _draw_centered_shaped_text(image, d_renderer, text, CHART_SIZE / 2, curr_y, color)
            else:
                d_font = _unicode_font(size)
                _draw_centered_text(draw, text, CHART_SIZE / 2, curr_y, d_font, color)
            curr_y += 22 if text == chart_info.date else 20

    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _render_english_grid_png(
    cells: tuple[ChartCell, ...],
    chart_info: ChartInfo | None = None,
    lines: tuple[tuple[int, int, int, int], ...] | None = None,
    info_box_rect: tuple[int, int, int, int] | None = None,
) -> bytes:
    image = Image.new("RGB", (CHART_SIZE, CHART_SIZE), "white")
    draw = ImageDraw.Draw(image)
    grid_lines = lines if lines is not None else _grid_lines()
    for line in grid_lines:
        draw.line(_png_line(line), fill=(17, 17, 17), width=2)

    if info_box_rect and info_box_rect != (171, 171, 170, 170):
        bx, by, bw, bh = info_box_rect
        draw.rectangle([bx, by, bx + bw, by + bh], fill=(255, 255, 255), outline=(17, 17, 17), width=1)

    top_font = _english_font(16)

    for cell in cells:
        if cell.top_label_pos:
            top_x, top_y = cell.top_label_pos
            _draw_centered_text(draw, cell.top_label, top_x, top_y, top_font, (34, 34, 34))
        else:
            x = cell.column * CELL_SIZE
            y = cell.row * CELL_SIZE
            draw.text((x + 8, y + 5), cell.top_label, font=top_font, fill=(34, 34, 34))

        display_lines = _display_lines(cell.labels)
        if not display_lines:
            continue
        font = _english_font(20) if len(display_lines) < 3 else _english_font(15)
        line_height = 24 if len(display_lines) < 3 else 18
        total_height = len(display_lines) * line_height

        if cell.center_pos:
            cx, cy = cell.center_pos
            start_y = cy - total_height / 2 + line_height / 2
        else:
            cx = cell.column * CELL_SIZE + CELL_SIZE / 2
            y = cell.row * CELL_SIZE
            start_y = y + max(28, (CELL_SIZE - total_height) / 2 + line_height / 2)

        for index, label in enumerate(display_lines):
            if not label:
                continue
            center_y = start_y + index * line_height
            _draw_centered_text(draw, label, cx, center_y, font)

    if chart_info:
        title_parts = chart_info.title.split(" - ", 1) if " - " in chart_info.title else [chart_info.title]
        if info_box_rect:
            _, by, _, bh = info_box_rect
            box_cy = by + bh / 2
            curr_y = box_cy - 40 if len(title_parts) > 1 else box_cy - 30
        else:
            curr_y = 216 if len(title_parts) > 1 else 226

        for idx, t_text in enumerate(title_parts):
            t_size = 15 if (len(t_text) > 14 or len(title_parts) > 1) else 18
            t_font = _english_font(t_size)
            _draw_centered_text(draw, t_text, CHART_SIZE / 2, curr_y, t_font, (17, 17, 17))
            curr_y += 22 if len(title_parts) > 1 else 26

        curr_y += 2
        for text, size, color in (
            (chart_info.date, 13, (51, 51, 51)),
            (chart_info.time, 13, (51, 51, 51)),
            (chart_info.location, 10, (51, 51, 51)),
        ):
            d_font = _english_font(size)
            _draw_centered_text(draw, text, CHART_SIZE / 2, curr_y, d_font, color)
            curr_y += 22 if text == chart_info.date else 20

    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def render_grid_png(
    cells: tuple[ChartCell, ...],
    chart_info: ChartInfo | None = None,
    language: str = "en",
    lines: tuple[tuple[int, int, int, int], ...] | None = None,
    info_box_rect: tuple[int, int, int, int] | None = None,
) -> bytes:
    if language != "en":
        return _render_unicode_grid_png(cells, chart_info, lines, info_box_rect)
    return _render_english_grid_png(cells, chart_info, lines, info_box_rect)
