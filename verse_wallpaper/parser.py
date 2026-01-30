"""Reference parsing for Bible references."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .constants import find_book


@dataclass(frozen=True)
class ParsedReference:
    book_number: int
    chapter: int
    verse: int | None = None


REFERENCE_RE = re.compile(
    r"^(?P<book>[1-3]?\s?[A-Za-z\.\s]+)\s+(?P<chapter>\d+)(?::(?P<verse>\d+))?$",
    re.IGNORECASE,
)


def parse_reference(text: str) -> ParsedReference | None:
    match = REFERENCE_RE.match(text.strip())
    if not match:
        return None
    book_text = match.group("book").strip()
    chapter = int(match.group("chapter"))
    verse = match.group("verse")
    book = find_book(book_text)
    if not book:
        return None
    return ParsedReference(
        book_number=book.number,
        chapter=chapter,
        verse=int(verse) if verse else None,
    )
