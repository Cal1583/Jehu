"""Helpers for Strong's number parsing and stoplist generation."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .state import app_data_dir


STRONGS_TAG_RE = re.compile(r"\{([GH]\d+)\}")


def strip_strongs_tags(text: str) -> str:
    """Remove Strong's tags from verse text for display."""
    return STRONGS_TAG_RE.sub("", text)


def extract_strongs_ids(text: str) -> list[str]:
    """Extract Strong's IDs (e.g., H7225) from verse text."""
    return STRONGS_TAG_RE.findall(text)


@dataclass(frozen=True)
class StrongsStoplist:
    ids: frozenset[str]
    top_n: int
    source: str

    def filter_ids(self, ids: Iterable[str], include_common: bool = False) -> list[str]:
        """Filter IDs using the stoplist unless include_common is True."""
        if include_common:
            return list(ids)
        return [strong_id for strong_id in ids if strong_id not in self.ids]


def load_or_create_stoplist(
    db_path: Path,
    all_verse_texts: Iterable[str],
    *,
    top_n: int = 50,
    extra_ids: Iterable[str] | None = None,
) -> StrongsStoplist:
    """Load a cached stoplist or compute it from the most frequent Strong's IDs."""
    cache_path = _stoplist_cache_path(db_path)
    cached = _read_cached_stoplist(cache_path, db_path, top_n)
    if cached:
        return cached
    stoplist = _build_stoplist_from_texts(all_verse_texts, top_n=top_n, extra_ids=extra_ids)
    _write_cached_stoplist(cache_path, db_path, stoplist)
    return stoplist


def _build_stoplist_from_texts(
    all_verse_texts: Iterable[str],
    *,
    top_n: int,
    extra_ids: Iterable[str] | None = None,
) -> StrongsStoplist:
    counter: Counter[str] = Counter()
    for text in all_verse_texts:
        counter.update(extract_strongs_ids(text))
    most_common = [strong_id for strong_id, _ in counter.most_common(top_n)]
    ids = set(most_common)
    if extra_ids:
        ids.update(extra_ids)
    return StrongsStoplist(ids=frozenset(ids), top_n=top_n, source="auto")


def _stoplist_cache_path(db_path: Path) -> Path:
    cache_dir = app_data_dir() / "strongs_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"stoplist_{db_path.stem}.json"


def _read_cached_stoplist(
    cache_path: Path,
    db_path: Path,
    top_n: int,
) -> StrongsStoplist | None:
    if not cache_path.exists():
        return None
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if (
        data.get("db_path") != str(db_path)
        or data.get("db_mtime") != db_path.stat().st_mtime
        or data.get("top_n") != top_n
    ):
        return None
    ids = frozenset(data.get("ids", []))
    return StrongsStoplist(ids=ids, top_n=top_n, source="cache")


def _write_cached_stoplist(
    cache_path: Path,
    db_path: Path,
    stoplist: StrongsStoplist,
) -> None:
    payload = {
        "db_path": str(db_path),
        "db_mtime": db_path.stat().st_mtime,
        "top_n": stoplist.top_n,
        "ids": sorted(stoplist.ids),
    }
    cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
