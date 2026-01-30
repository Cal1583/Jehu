"""Wallpaper rendering for the Verse Wallpaper app."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import importlib.util

from PIL import Image, ImageDraw, ImageFont

from .backgrounds import paint_palette_background
from .db import book_name

if importlib.util.find_spec("squarify"):
    import squarify  # type: ignore
else:  # pragma: no cover
    squarify = None


@dataclass(frozen=True)
class RenderContext:
    width: int = 3440
    height: int = 1440


@dataclass(frozen=True)
class ScriptureContent:
    header: str
    translation: str
    lines: list[str]
    is_chapter: bool


@dataclass(frozen=True)
class AnalyticsContent:
    book_lengths: list[tuple[int, int]]
    current_book: int
    current_chapter: int
    current_verse: int
    progress_percent: float
    days_advanced: int
    key_names: list[str]
    repeated_concepts: list[str]


class WallpaperRenderer:
    def __init__(self, context: RenderContext | None = None) -> None:
        self.context = context or RenderContext()
        self.background_color = (238, 238, 238)
        self.page_color = (250, 249, 246)
        self.metrics_page_color = (250, 249, 246)
        self.text_color = (40, 40, 40)
        self.accent_color = (90, 90, 90)
        self.shadow_color = (210, 210, 210)
        self.treemap_fill_current = (200, 210, 230)
        self.treemap_fill_remaining = (230, 230, 230)
        self.treemap_outline_color = (160, 160, 160)
        self.metrics_text_color = (40, 40, 40)
        self.font_body = self._load_font(28)
        self.font_body_small = self._load_font(24)
        self.font_header = self._load_font(36, bold=True)
        self.font_header_small = self._load_font(30, bold=True)
        self.font_label = self._load_font(22)

    def _load_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        candidates = [
            "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for path in candidates:
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
        return ImageFont.load_default()

    def render(
        self,
        scripture: ScriptureContent,
        analytics: AnalyticsContent,
        palette_colors: list[tuple[int, int, int]] | None = None,
        dark_mode: bool = False,
    ) -> Image.Image:
        self._apply_theme(dark_mode)
        image = Image.new("RGB", (self.context.width, self.context.height), self.background_color)
        if palette_colors:
            paint_palette_background(image, palette_colors)
        draw = ImageDraw.Draw(image)
        page_margin = 120
        gutter_width = 40
        page_width = (self.context.width - page_margin * 2 - gutter_width) // 2
        page_height = self.context.height - page_margin * 2
        left_x = page_margin
        right_x = left_x + page_width + gutter_width
        top_y = page_margin

        shadow_offset = 8
        draw.rectangle(
            [left_x + shadow_offset, top_y + shadow_offset, left_x + page_width + shadow_offset, top_y + page_height + shadow_offset],
            fill=self.shadow_color,
        )
        draw.rectangle(
            [right_x + shadow_offset, top_y + shadow_offset, right_x + page_width + shadow_offset, top_y + page_height + shadow_offset],
            fill=self.shadow_color,
        )
        draw.rectangle([left_x, top_y, left_x + page_width, top_y + page_height], fill=self.metrics_page_color)
        draw.rectangle([right_x, top_y, right_x + page_width, top_y + page_height], fill=self.page_color)
        spine_x = left_x + page_width + gutter_width // 2
        draw.line([spine_x, top_y, spine_x, top_y + page_height], fill=self.accent_color, width=2)

        self._draw_scripture(draw, right_x, top_y, page_width, page_height, scripture)
        self._draw_analytics(draw, left_x, top_y, page_width, page_height, analytics)

        return image

    def _apply_theme(self, dark_mode: bool) -> None:
        if dark_mode:
            self.page_color = (18, 18, 18)
            self.text_color = (234, 234, 234)
            self.accent_color = (200, 200, 200)
            self.shadow_color = (10, 10, 10)
        else:
            self.page_color = (250, 249, 246)
            self.text_color = (40, 40, 40)
            self.accent_color = (90, 90, 90)
            self.shadow_color = (210, 210, 210)

    def _draw_scripture(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        width: int,
        height: int,
        scripture: ScriptureContent,
    ) -> None:
        padding = 50
        header_font = self.font_header if scripture.is_chapter else self.font_header_small
        header_text = scripture.header
        draw.text((x + padding, y + padding), header_text, fill=self.text_color, font=header_font)
        translation_text = scripture.translation
        header_height = header_font.getbbox(header_text)[3]
        draw.text(
            (x + padding, y + padding + header_height + 8),
            translation_text,
            fill=self.accent_color,
            font=self.font_label,
        )
        content_top = y + padding + header_height + 50
        content_height = height - (content_top - y) - padding
        content_width = width - padding * 2

        font = self.font_body
        column_gap = 30
        columns = 1
        lines = scripture.lines

        def render_lines(col_x: int, col_width: int, line_font: ImageFont.FreeTypeFont) -> int:
            line_height = line_font.getbbox("Ag")[3] + 8
            max_lines = content_height // line_height
            line_index = 0
            y_pos = content_top
            for line in lines:
                wrapped = wrap_text(line, line_font, col_width)
                for segment in wrapped:
                    if line_index >= max_lines:
                        return line_index
                    draw.text((col_x, y_pos), segment, fill=self.text_color, font=line_font)
                    y_pos += line_height
                    line_index += 1
            return line_index

        line_height = font.getbbox("Ag")[3] + 8
        max_lines = content_height // line_height
        if len(lines) > max_lines:
            columns = 2

        if columns == 1:
            render_lines(x + padding, content_width, font)
            return

        column_width = (content_width - column_gap) // 2
        total_lines = sum(len(wrap_text(line, font, column_width)) for line in lines)
        max_lines = content_height // line_height * 2
        if total_lines > max_lines:
            font = self.font_body_small
            line_height = font.getbbox("Ag")[3] + 8
        col_x_left = x + padding
        col_x_right = x + padding + column_width + column_gap
        line_height = font.getbbox("Ag")[3] + 8
        max_lines_per_column = content_height // line_height
        line_index = 0
        y_pos = content_top
        col = 0
        for line in lines:
            wrapped = wrap_text(line, font, column_width)
            for segment in wrapped:
                if line_index >= max_lines_per_column:
                    col += 1
                    if col > 1:
                        return
                    line_index = 0
                    y_pos = content_top
                col_x = col_x_left if col == 0 else col_x_right
                draw.text((col_x, y_pos), segment, fill=self.text_color, font=font)
                y_pos += line_height
                line_index += 1

    def _draw_analytics(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        width: int,
        height: int,
        analytics: AnalyticsContent,
    ) -> None:
        padding = 40
        header = "Reading Progress"
        draw.text((x + padding, y + padding), header, fill=self.metrics_text_color, font=self.font_header_small)
        header_height = self.font_header_small.getbbox(header)[3]
        chart_top = y + padding + header_height + 20
        label_line_height = self.font_label.getbbox("Ag")[3] + 8
        stats_lines_height = label_line_height * 3
        summary_title_height = self.font_label.getbbox("Ag")[3] + 6
        summary_item_height = self.font_body_small.getbbox("Ag")[3] + 4
        key_names_height = summary_title_height + summary_item_height * 5
        repeated_concepts_height = summary_title_height + summary_item_height * 8
        bottom_reserved = 20 + stats_lines_height + 6 + key_names_height + 10 + repeated_concepts_height + padding
        chart_height = height - (chart_top - y) - bottom_reserved
        chart_width = width - padding * 2
        chart_x = x + padding
        chart_y = chart_top

        rects = treemap_rectangles(analytics.book_lengths, chart_x, chart_y, chart_width, chart_height)
        current_index = next(
            (index for index, (book, _) in enumerate(analytics.book_lengths) if book == analytics.current_book),
            0,
        )
        for index, rect in enumerate(rects):
            book_num, size = analytics.book_lengths[index]
            fill = self.treemap_fill_current if index <= current_index else self.treemap_fill_remaining
            draw.rectangle(rect, fill=fill, outline=self.treemap_outline_color, width=1)
            label = book_name(book_num)
            label_font = self.font_label
            if rect[2] - rect[0] > 120 and rect[3] - rect[1] > 40:
                draw.text((rect[0] + 6, rect[1] + 6), label, fill=self.metrics_text_color, font=label_font)

        stats_y = chart_y + chart_height + 20
        stats = [
            f"Current: {book_name(analytics.current_book)} {analytics.current_chapter}:{analytics.current_verse}",
            f"Progress: {analytics.progress_percent:.1f}%",
            f"Days advanced: {analytics.days_advanced}",
        ]
        for stat in stats:
            draw.text((x + padding, stats_y), stat, fill=self.metrics_text_color, font=self.font_label)
            stats_y += self.font_label.getbbox(stat)[3] + 8

        stats_y += 6
        stats_y = self._draw_summary_block(
            draw,
            x + padding,
            stats_y,
            "Key Names",
            analytics.key_names[:5],
        )
        stats_y += 10
        self._draw_summary_block(
            draw,
            x + padding,
            stats_y,
            "Repeated Concepts",
            analytics.repeated_concepts[:8],
        )

    def _draw_summary_block(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        title: str,
        items: list[str],
    ) -> int:
        draw.text((x, y), title, fill=self.metrics_text_color, font=self.font_label)
        y += self.font_label.getbbox(title)[3] + 6
        if not items:
            items = ["—"]
        for item in items:
            draw.text((x + 10, y), item, fill=self.metrics_text_color, font=self.font_body_small)
            y += self.font_body_small.getbbox(item)[3] + 4
        return y


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if font.getlength(test) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def treemap_rectangles(
    book_lengths: list[tuple[int, int]],
    x: int,
    y: int,
    width: int,
    height: int,
) -> list[tuple[int, int, int, int]]:
    sizes = [length for _, length in book_lengths]
    if not sizes:
        return []
    if squarify:
        normalized = squarify.normalize_sizes(sizes, width, height)
        rects = squarify.squarify(normalized, x, y, width, height)
        return [
            (int(r["x"]), int(r["y"]), int(r["x"] + r["dx"]), int(r["y"] + r["dy"]))
            for r in rects
        ]
    total = sum(sizes)
    row_height = height // math.ceil(len(sizes) ** 0.5)
    rects = []
    row_y = y
    row_x = x
    remaining_width = width
    current_row = []
    current_sum = 0
    row_capacity = width * row_height
    for size in sizes:
        if (current_sum + size) / total * width * height > row_capacity and current_row:
            rects.extend(_row_to_rects(current_row, row_x, row_y, width, row_height, total, height))
            row_y += row_height
            current_row = [size]
            current_sum = size
        else:
            current_row.append(size)
            current_sum += size
    if current_row:
        rects.extend(_row_to_rects(current_row, row_x, row_y, width, row_height, total, height))
    return rects


def _row_to_rects(
    sizes: list[int],
    x: int,
    y: int,
    width: int,
    row_height: int,
    total: int,
    total_height: int,
) -> list[tuple[int, int, int, int]]:
    rects = []
    row_total = sum(sizes)
    current_x = x
    for size in sizes:
        rect_width = max(1, int(width * (size / row_total)))
        rects.append((current_x, y, current_x + rect_width, y + row_height))
        current_x += rect_width
    return rects
