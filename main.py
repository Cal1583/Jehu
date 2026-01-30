"""Verse Wallpaper main entry point.

Dependencies:
- pip install PySide6 Pillow
- optional: pip install squarify

Run GUI:
    python main.py

Run daily Task Scheduler mode:
    python main.py --daily
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from verse_wallpaper.cursor import advance_if_needed
from verse_wallpaper.db import BibleDB, available_databases
from verse_wallpaper.renderer import AnalyticsContent, ScriptureContent, WallpaperRenderer
from verse_wallpaper.state import StateStore
from verse_wallpaper.ui import VerseWallpaperApp
from verse_wallpaper.wallpaper import save_wallpaper, set_wallpaper
from verse_wallpaper.db import book_name


def _find_db_path(state_path: str | None) -> Path | None:
    if state_path:
        path = Path(state_path)
        if path.exists():
            return path
    search_root = Path.cwd() / "truth"
    candidates = available_databases(search_root) if search_root.exists() else []
    return candidates[0] if candidates else None


def run_daily() -> int:
    state_store = StateStore()
    state = state_store.load()
    db_path = _find_db_path(state.db_path)
    if not db_path:
        print("No Bible database found. Please run the GUI to configure.")
        return 1
    bible = BibleDB(db_path)
    state = advance_if_needed(state, bible)
    translation = bible.list_translations()[0]

    book = state.cursor.book
    chapter = state.cursor.chapter
    verse = state.cursor.verse
    if state.mode == "chapter":
        verses = bible.chapter_text(book, chapter)
        lines = [f"{num} {text}" for num, text in verses]
        header = f"{book_name(book)} {chapter}"
        is_chapter = True
    else:
        text = bible.verse_text(book, chapter, verse)
        lines = [text]
        header = f"{book_name(book)} {chapter}:{verse}"
        is_chapter = False
    scripture = ScriptureContent(
        header=header,
        translation=translation.name,
        lines=lines,
        is_chapter=is_chapter,
    )

    book_lengths = bible.book_lengths()
    total_verses = sum(length for _, length in book_lengths)
    verse_index = bible.verse_index(book, chapter, verse)
    progress_percent = (verse_index / total_verses * 100) if total_verses else 0.0
    days_advanced = verse_index if state.mode == "verse" else chapter
    analytics = AnalyticsContent(
        book_lengths=book_lengths,
        current_book=book,
        current_chapter=chapter,
        current_verse=verse,
        progress_percent=progress_percent,
        days_advanced=days_advanced,
    )

    renderer = WallpaperRenderer()
    image = renderer.render(scripture, analytics)
    path = save_wallpaper(image)
    set_wallpaper(path)

    state_store.save(state)
    bible.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Verse Wallpaper")
    parser.add_argument("--daily", action="store_true", help="Run daily wallpaper update")
    args = parser.parse_args()

    if args.daily:
        return run_daily()

    state_store = StateStore()
    app = VerseWallpaperApp(state_store)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
