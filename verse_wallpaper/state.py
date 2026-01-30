"""State persistence for Verse Wallpaper."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def app_data_dir() -> Path:
    appdata = Path.home() / ".verse_wallpaper"
    if "APPDATA" in os.environ:
        appdata = Path(os.environ["APPDATA"]) / "VerseWallpaper"
    return appdata


@dataclass
class Cursor:
    book: int = 1
    chapter: int = 1
    verse: int = 1


@dataclass
class AppState:
    translation_id: str | None = None
    mode: str = "chapter"
    cursor: Cursor = field(default_factory=Cursor)
    last_advance_date: str | None = None
    testament_filter: str = "all"
    selected_book: int = 1
    selected_chapter: int = 1
    selected_verse: int = 1
    db_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "translation_id": self.translation_id,
            "mode": self.mode,
            "cursor": {
                "book": self.cursor.book,
                "chapter": self.cursor.chapter,
                "verse": self.cursor.verse,
            },
            "last_advance_date": self.last_advance_date,
            "testament_filter": self.testament_filter,
            "selected_book": self.selected_book,
            "selected_chapter": self.selected_chapter,
            "selected_verse": self.selected_verse,
            "db_path": self.db_path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppState":
        cursor_data = data.get("cursor", {})
        cursor = Cursor(
            book=int(cursor_data.get("book", 1)),
            chapter=int(cursor_data.get("chapter", 1)),
            verse=int(cursor_data.get("verse", 1)),
        )
        return cls(
            translation_id=data.get("translation_id"),
            mode=data.get("mode", "chapter"),
            cursor=cursor,
            last_advance_date=data.get("last_advance_date"),
            testament_filter=data.get("testament_filter", "all"),
            selected_book=int(data.get("selected_book", cursor.book)),
            selected_chapter=int(data.get("selected_chapter", cursor.chapter)),
            selected_verse=int(data.get("selected_verse", cursor.verse)),
            db_path=data.get("db_path"),
        )


class StateStore:
    def __init__(self, path: Path | None = None) -> None:
        self.base_dir = path or app_data_dir()
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.base_dir / "settings.json"

    def load(self) -> AppState:
        if not self.state_path.exists():
            return AppState()
        data = json.loads(self.state_path.read_text(encoding="utf-8"))
        return AppState.from_dict(data)

    def save(self, state: AppState) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(state.to_dict(), indent=2), encoding="utf-8"
        )
