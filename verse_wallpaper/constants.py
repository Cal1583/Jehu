"""Constants and canonical metadata for Bible books."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BookInfo:
    number: int
    name: str
    testament: str
    abbreviations: tuple[str, ...]


BOOKS: tuple[BookInfo, ...] = (
    BookInfo(1, "Genesis", "OT", ("gen", "ge", "gn")),
    BookInfo(2, "Exodus", "OT", ("ex", "exo", "exod")),
    BookInfo(3, "Leviticus", "OT", ("lev", "le", "lv")),
    BookInfo(4, "Numbers", "OT", ("num", "nu", "nm", "nb")),
    BookInfo(5, "Deuteronomy", "OT", ("deut", "de", "dt")),
    BookInfo(6, "Joshua", "OT", ("josh", "jos", "jsh")),
    BookInfo(7, "Judges", "OT", ("judg", "jdg", "jg")),
    BookInfo(8, "Ruth", "OT", ("ruth", "ru")),
    BookInfo(9, "1 Samuel", "OT", ("1sam", "1sa", "i sam", "1sm")),
    BookInfo(10, "2 Samuel", "OT", ("2sam", "2sa", "ii sam", "2sm")),
    BookInfo(11, "1 Kings", "OT", ("1kings", "1ki", "i kings", "1kg")),
    BookInfo(12, "2 Kings", "OT", ("2kings", "2ki", "ii kings", "2kg")),
    BookInfo(13, "1 Chronicles", "OT", ("1chron", "1ch", "i chron", "1chr")),
    BookInfo(14, "2 Chronicles", "OT", ("2chron", "2ch", "ii chron", "2chr")),
    BookInfo(15, "Ezra", "OT", ("ezra", "ezr")),
    BookInfo(16, "Nehemiah", "OT", ("neh", "ne")),
    BookInfo(17, "Esther", "OT", ("est", "es")),
    BookInfo(18, "Job", "OT", ("job", "jb")),
    BookInfo(19, "Psalms", "OT", ("ps", "psalm", "psa", "pss")),
    BookInfo(20, "Proverbs", "OT", ("prov", "pr", "prv")),
    BookInfo(21, "Ecclesiastes", "OT", ("eccl", "ecc", "qoh")),
    BookInfo(22, "Song of Solomon", "OT", ("song", "song of solomon", "sos", "so")),
    BookInfo(23, "Isaiah", "OT", ("isa", "is")),
    BookInfo(24, "Jeremiah", "OT", ("jer", "jr")),
    BookInfo(25, "Lamentations", "OT", ("lam", "la")),
    BookInfo(26, "Ezekiel", "OT", ("ezek", "eze", "ezk")),
    BookInfo(27, "Daniel", "OT", ("dan", "da", "dn")),
    BookInfo(28, "Hosea", "OT", ("hos", "ho")),
    BookInfo(29, "Joel", "OT", ("joel", "jl")),
    BookInfo(30, "Amos", "OT", ("amos", "am")),
    BookInfo(31, "Obadiah", "OT", ("obad", "ob")),
    BookInfo(32, "Jonah", "OT", ("jon", "jnh")),
    BookInfo(33, "Micah", "OT", ("mic", "mc")),
    BookInfo(34, "Nahum", "OT", ("nah", "na")),
    BookInfo(35, "Habakkuk", "OT", ("hab", "hb")),
    BookInfo(36, "Zephaniah", "OT", ("zeph", "zep", "zp")),
    BookInfo(37, "Haggai", "OT", ("hag", "hg")),
    BookInfo(38, "Zechariah", "OT", ("zech", "zec", "zc")),
    BookInfo(39, "Malachi", "OT", ("mal", "ml")),
    BookInfo(40, "Matthew", "NT", ("matt", "mt")),
    BookInfo(41, "Mark", "NT", ("mark", "mrk", "mk")),
    BookInfo(42, "Luke", "NT", ("luke", "lk")),
    BookInfo(43, "John", "NT", ("john", "jn", "jhn")),
    BookInfo(44, "Acts", "NT", ("acts", "ac")),
    BookInfo(45, "Romans", "NT", ("rom", "ro", "rm")),
    BookInfo(46, "1 Corinthians", "NT", ("1cor", "1co", "i cor", "1corinthians")),
    BookInfo(47, "2 Corinthians", "NT", ("2cor", "2co", "ii cor", "2corinthians")),
    BookInfo(48, "Galatians", "NT", ("gal", "ga")),
    BookInfo(49, "Ephesians", "NT", ("eph", "ep")),
    BookInfo(50, "Philippians", "NT", ("phil", "php", "ph")),
    BookInfo(51, "Colossians", "NT", ("col", "co")),
    BookInfo(52, "1 Thessalonians", "NT", ("1thess", "1th", "i thess", "1thes")),
    BookInfo(53, "2 Thessalonians", "NT", ("2thess", "2th", "ii thess", "2thes")),
    BookInfo(54, "1 Timothy", "NT", ("1tim", "1ti", "i tim", "1tm")),
    BookInfo(55, "2 Timothy", "NT", ("2tim", "2ti", "ii tim", "2tm")),
    BookInfo(56, "Titus", "NT", ("titus", "ti")),
    BookInfo(57, "Philemon", "NT", ("philem", "phm", "pm")),
    BookInfo(58, "Hebrews", "NT", ("heb", "he")),
    BookInfo(59, "James", "NT", ("jas", "jm")),
    BookInfo(60, "1 Peter", "NT", ("1pet", "1pe", "i pet", "1pt")),
    BookInfo(61, "2 Peter", "NT", ("2pet", "2pe", "ii pet", "2pt")),
    BookInfo(62, "1 John", "NT", ("1john", "1jn", "i jn", "1j")),
    BookInfo(63, "2 John", "NT", ("2john", "2jn", "ii jn", "2j")),
    BookInfo(64, "3 John", "NT", ("3john", "3jn", "iii jn", "3j")),
    BookInfo(65, "Jude", "NT", ("jude", "jud")),
    BookInfo(66, "Revelation", "NT", ("rev", "re", "rv")),
)

BOOK_NAME_BY_NUMBER = {book.number: book.name for book in BOOKS}
BOOK_BY_NORMALIZED = {}

for book in BOOKS:
    normalized_name = book.name.lower().replace(" ", "")
    BOOK_BY_NORMALIZED[normalized_name] = book
    for abbr in book.abbreviations:
        BOOK_BY_NORMALIZED[abbr.lower().replace(" ", "")] = book


def normalize_book_key(value: str) -> str:
    return value.lower().replace(".", "").replace(" ", "")


def find_book(value: str) -> BookInfo | None:
    key = normalize_book_key(value)
    return BOOK_BY_NORMALIZED.get(key)
