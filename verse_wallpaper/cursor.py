"""Cursor advancement logic for daily reading."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

from .constants import BOOKS
from .state import AppState, Cursor
from .db import BibleDB


def _today_str() -> str:
    return date.today().isoformat()


def advance_if_needed(state: AppState, bible: BibleDB) -> AppState:
    today = _today_str()
    if state.last_advance_date == today:
        return state
    if state.mode == "chapter":
        cursor = advance_chapter(state.cursor, bible)
    else:
        cursor = advance_verse(state.cursor, bible)
    state.cursor = cursor
    state.last_advance_date = today
    state.selected_book = cursor.book
    state.selected_chapter = cursor.chapter
    state.selected_verse = cursor.verse
    return state


def advance_chapter(cursor: Cursor, bible: BibleDB) -> Cursor:
    max_chapter = bible.max_chapter(cursor.book)
    if cursor.chapter < max_chapter:
        return replace(cursor, chapter=cursor.chapter + 1, verse=1)
    next_book = cursor.book + 1
    if next_book > len(BOOKS):
        next_book = 1
    return Cursor(book=next_book, chapter=1, verse=1)


def advance_verse(cursor: Cursor, bible: BibleDB) -> Cursor:
    max_verse = bible.max_verse(cursor.book, cursor.chapter)
    if cursor.verse < max_verse:
        return replace(cursor, verse=cursor.verse + 1)
    max_chapter = bible.max_chapter(cursor.book)
    if cursor.chapter < max_chapter:
        return Cursor(book=cursor.book, chapter=cursor.chapter + 1, verse=1)
    next_book = cursor.book + 1
    if next_book > len(BOOKS):
        next_book = 1
    return Cursor(book=next_book, chapter=1, verse=1)
