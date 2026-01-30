"""Wallpaper file management and Windows setting."""

from __future__ import annotations

import ctypes
from pathlib import Path

from .state import app_data_dir

SPI_SETDESKWALLPAPER = 20
SPIF_UPDATEINIFILE = 0x1
SPIF_SENDWININICHANGE = 0x2


def wallpaper_path() -> Path:
    base = app_data_dir()
    base.mkdir(parents=True, exist_ok=True)
    return base / "current_wallpaper.png"


def save_wallpaper(image) -> Path:
    path = wallpaper_path()
    image.save(path, "PNG")
    return path


def set_wallpaper(path: Path) -> None:
    ctypes.windll.user32.SystemParametersInfoW(
        SPI_SETDESKWALLPAPER,
        0,
        str(path),
        SPIF_UPDATEINIFILE | SPIF_SENDWININICHANGE,
    )
