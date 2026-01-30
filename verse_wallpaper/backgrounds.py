"""Background painting helpers."""

from __future__ import annotations

import math
from typing import Iterable

from PIL import Image, ImageDraw


def paint_palette_background(
    canvas: Image.Image, colors: Iterable[tuple[int, int, int]]
) -> None:
    palette = list(colors)
    if not palette:
        return
    width, height = canvas.size
    band_count = len(palette)
    band_width = max(1, math.ceil(width / band_count))
    draw = ImageDraw.Draw(canvas)
    for index, color in enumerate(palette):
        left = index * band_width
        right = width if index == band_count - 1 else min(width, left + band_width)
        draw.rectangle([left, 0, right, height], fill=color)
