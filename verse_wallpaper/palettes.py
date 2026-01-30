"""Palette loading helpers for Verse Wallpaper."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Palette:
    name: str
    colors: list[tuple[int, int, int]]


def _default_palette() -> Palette:
    return Palette(
        name="Default",
        colors=[(238, 238, 238), (250, 249, 246), (220, 220, 220)],
    )


def _parse_color(value: Any) -> tuple[int, int, int] | None:
    if isinstance(value, dict) and "hex" in value:
        return _parse_color(value["hex"])
    if isinstance(value, str):
        hex_value = value.strip()
        if hex_value.startswith("#"):
            hex_value = hex_value[1:]
        if len(hex_value) == 3:
            hex_value = "".join(char * 2 for char in hex_value)
        if len(hex_value) != 6:
            return None
        try:
            return (
                int(hex_value[0:2], 16),
                int(hex_value[2:4], 16),
                int(hex_value[4:6], 16),
            )
        except ValueError:
            return None
    if isinstance(value, (list, tuple)) and len(value) == 3:
        try:
            rgb = tuple(int(channel) for channel in value)
        except (TypeError, ValueError):
            return None
        if any(channel < 0 or channel > 255 for channel in rgb):
            return None
        return rgb  # type: ignore[return-value]
    return None


def _parse_palette_entry(entry: Any) -> Palette | None:
    if not isinstance(entry, dict):
        return None
    name = entry.get("name")
    colors = entry.get("colors")
    if not name or not isinstance(colors, list):
        return None
    parsed_colors = []
    for color in colors:
        parsed = _parse_color(color)
        if parsed:
            parsed_colors.append(parsed)
    if not parsed_colors:
        return None
    return Palette(name=str(name), colors=parsed_colors)


def load_palettes(json_path: Path) -> list[Palette]:
    default = _default_palette()
    if not json_path.exists():
        return [default]
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [default]

    entries: list[Any] = []
    if isinstance(data, list):
        entries = data
    elif isinstance(data, dict):
        if isinstance(data.get("palettes"), list):
            entries = data.get("palettes", [])
        else:
            entries = [
                {"name": name, "colors": colors}
                for name, colors in data.items()
                if isinstance(colors, list)
            ]

    palettes: list[Palette] = []
    seen_names = set()
    for entry in entries:
        palette = _parse_palette_entry(entry)
        if not palette or palette.name in seen_names:
            continue
        palettes.append(palette)
        seen_names.add(palette.name)

    if default.name not in seen_names:
        palettes.insert(0, default)
    if not palettes:
        return [default]
    return palettes


def get_palette_map(paths: list[Path]) -> dict[str, Palette]:
    palettes: list[Palette] | None = None
    for path in paths:
        if path.exists():
            palettes = load_palettes(path)
            break
    if palettes is None:
        palettes = load_palettes(paths[0]) if paths else [_default_palette()]
    return {palette.name: palette for palette in palettes}
