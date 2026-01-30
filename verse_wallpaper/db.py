"""SQLite adapter for Bible data."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .constants import BOOKS, BOOK_NAME_BY_NUMBER
from .strongs import (
    StrongsStoplist,
    extract_strongs_ids,
    load_or_create_stoplist,
    strip_strongs_tags,
)


@dataclass(frozen=True)
class Translation:
    id: str
    name: str


@dataclass(frozen=True)
class SchemaMapping:
    verse_table: str
    book_column: str
    chapter_column: str
    verse_column: str
    text_column: str
    meta_table: str | None = None
    meta_key_column: str | None = None
    meta_value_column: str | None = None


class BibleDB:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path)
        self.connection.row_factory = sqlite3.Row
        self.schema = self._detect_schema()
        self._strongs_stoplist: StrongsStoplist | None = None
        self._strongs_top_n = 50
        self.include_common_strongs = False

    @property
    def strongs_stoplist(self) -> StrongsStoplist:
        if self._strongs_stoplist is None:
            self._strongs_stoplist = load_or_create_stoplist(
                self.db_path,
                self._all_verse_texts(),
                top_n=self._strongs_top_n,
            )
        return self._strongs_stoplist

    def _detect_schema(self) -> SchemaMapping:
        cursor = self.connection.cursor()
        tables = {
            row[0].lower(): row[0]
            for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "verses" in tables:
            columns = {
                row[1].lower(): row[1]
                for row in cursor.execute(f"PRAGMA table_info({tables['verses']})")
            }
            required = {"book", "chapter", "verse"}
            if required.issubset(columns.keys()):
                text_column = columns.get("text") or columns.get("verse")
                return SchemaMapping(
                    verse_table=tables["verses"],
                    book_column=columns["book"],
                    chapter_column=columns["chapter"],
                    verse_column=columns["verse"],
                    text_column=text_column or "text",
                    meta_table=tables.get("meta"),
                    meta_key_column="field",
                    meta_value_column="value",
                )
        raise ValueError(
            "Unable to detect Bible schema. Expected a 'verses' table with book/chapter/verse columns."
        )

    def list_translations(self) -> list[Translation]:
        translations: list[Translation] = []
        if self.schema.meta_table:
            cursor = self.connection.cursor()
            row = cursor.execute(
                f"SELECT {self.schema.meta_value_column} FROM {self.schema.meta_table} "
                f"WHERE {self.schema.meta_key_column}='name'"
            ).fetchone()
            name = row[0] if row else self.db_path.stem
            translations.append(Translation(id=self.db_path.stem, name=name))
        else:
            translations.append(Translation(id=self.db_path.stem, name=self.db_path.stem))
        return translations

    def list_books(self) -> list[tuple[int, str]]:
        return [(book.number, book.name) for book in BOOKS]

    def chapters_for_book(self, book_number: int) -> list[int]:
        cursor = self.connection.cursor()
        rows = cursor.execute(
            f"SELECT DISTINCT {self.schema.chapter_column} FROM {self.schema.verse_table} "
            f"WHERE {self.schema.book_column}=? ORDER BY {self.schema.chapter_column}",
            (book_number,),
        ).fetchall()
        return [int(row[0]) for row in rows]

    def verses_for_chapter(self, book_number: int, chapter: int) -> list[int]:
        cursor = self.connection.cursor()
        rows = cursor.execute(
            f"SELECT {self.schema.verse_column} FROM {self.schema.verse_table} "
            f"WHERE {self.schema.book_column}=? AND {self.schema.chapter_column}=? "
            f"ORDER BY {self.schema.verse_column}",
            (book_number, chapter),
        ).fetchall()
        return [int(row[0]) for row in rows]

    def chapter_text(self, book_number: int, chapter: int) -> list[tuple[int, str]]:
        cursor = self.connection.cursor()
        rows = cursor.execute(
            f"SELECT {self.schema.verse_column}, {self.schema.text_column} "
            f"FROM {self.schema.verse_table} WHERE {self.schema.book_column}=? "
            f"AND {self.schema.chapter_column}=? ORDER BY {self.schema.verse_column}",
            (book_number, chapter),
        ).fetchall()
        return [(int(row[0]), strip_strongs_tags(str(row[1]))) for row in rows]

    def verse_text(self, book_number: int, chapter: int, verse: int) -> str:
        cursor = self.connection.cursor()
        row = cursor.execute(
            f"SELECT {self.schema.text_column} FROM {self.schema.verse_table} "
            f"WHERE {self.schema.book_column}=? AND {self.schema.chapter_column}=? "
            f"AND {self.schema.verse_column}=?",
            (book_number, chapter, verse),
        ).fetchone()
        return strip_strongs_tags(str(row[0])) if row else ""

    def chapter_strongs_metrics(
        self, book_number: int, chapter: int
    ) -> tuple[dict[str, int], dict[str, int]]:
        """Return (vocabulary_counts, occurrence_counts) for Strong's IDs in a chapter."""
        cursor = self.connection.cursor()
        rows = cursor.execute(
            f"SELECT {self.schema.text_column} FROM {self.schema.verse_table} "
            f"WHERE {self.schema.book_column}=? AND {self.schema.chapter_column}=? "
            f"ORDER BY {self.schema.verse_column}",
            (book_number, chapter),
        ).fetchall()
        stoplist = self.strongs_stoplist
        vocabulary_counts: dict[str, int] = {}
        occurrence_counts: dict[str, int] = {}
        for row in rows:
            ids = extract_strongs_ids(str(row[0]))
            filtered = stoplist.filter_ids(ids, include_common=self.include_common_strongs)
            unique_ids = set(filtered)
            for strong_id in unique_ids:
                vocabulary_counts[strong_id] = vocabulary_counts.get(strong_id, 0) + 1
            for strong_id in filtered:
                occurrence_counts[strong_id] = occurrence_counts.get(strong_id, 0) + 1
        return vocabulary_counts, occurrence_counts

    def book_lengths(self) -> list[tuple[int, int]]:
        """Return (book_number, verse_count)."""
        cursor = self.connection.cursor()
        rows = cursor.execute(
            f"SELECT {self.schema.book_column}, COUNT(*) FROM {self.schema.verse_table} "
            f"GROUP BY {self.schema.book_column} ORDER BY {self.schema.book_column}"
        ).fetchall()
        return [(int(row[0]), int(row[1])) for row in rows]

    def max_chapter(self, book_number: int) -> int:
        chapters = self.chapters_for_book(book_number)
        return max(chapters) if chapters else 1

    def max_verse(self, book_number: int, chapter: int) -> int:
        verses = self.verses_for_chapter(book_number, chapter)
        return max(verses) if verses else 1

    def verse_index(self, book_number: int, chapter: int, verse: int) -> int:
        cursor = self.connection.cursor()
        row = cursor.execute(
            f"SELECT COUNT(*) FROM {self.schema.verse_table} "
            f"WHERE {self.schema.book_column}=? AND ("
            f"{self.schema.chapter_column} < ? OR "
            f"({self.schema.chapter_column}=? AND {self.schema.verse_column} <= ?))",
            (book_number, chapter, chapter, verse),
        ).fetchone()
        return int(row[0]) if row else 0

    def close(self) -> None:
        self.connection.close()

    def _all_verse_texts(self) -> Iterable[str]:
        cursor = self.connection.cursor()
        rows = cursor.execute(
            f"SELECT {self.schema.text_column} FROM {self.schema.verse_table}"
        ).fetchall()
        for row in rows:
            yield str(row[0])


def available_databases(root: Path) -> list[Path]:
    return sorted(root.glob("**/*.sqlite"))


def book_name(book_number: int) -> str:
    return BOOK_NAME_BY_NUMBER.get(book_number, f"Book {book_number}")
