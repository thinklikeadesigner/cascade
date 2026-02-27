"""Cascade level utilities — level ordering, file-to-level mapping, discovery."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

CascadeLevel = Literal["day", "week", "month", "quarter", "year"]

LEVELS_ASCENDING: list[CascadeLevel] = ["day", "week", "month", "quarter", "year"]


def get_next_level_up(level: CascadeLevel) -> CascadeLevel | None:
    """Return the next level up in the cascade, or None if already at year."""
    try:
        idx = LEVELS_ASCENDING.index(level)
    except ValueError:
        return None
    if idx == len(LEVELS_ASCENDING) - 1:
        return None
    return LEVELS_ASCENDING[idx + 1]


def is_above(a: CascadeLevel, b: CascadeLevel) -> bool:
    """Return True if level *a* is above level *b* in the cascade."""
    return LEVELS_ASCENDING.index(a) > LEVELS_ASCENDING.index(b)


_MONTH_PATTERN = re.compile(
    r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)-\d{4}\.md$"
)
_QUARTER_PATTERN = re.compile(r"^q\d-")
_YEAR_PATTERN = re.compile(r"^\d{4}-goals\.md$")


def file_to_level(filename: str) -> CascadeLevel | None:
    """Map a cascade data filename to its level. Returns None for non-cascade files."""
    name = Path(filename).name.lower()

    if name.startswith("day-"):
        return "day"
    if name.startswith("week-"):
        return "week"
    if _MONTH_PATTERN.match(name):
        return "month"
    if _QUARTER_PATTERN.match(name):
        return "quarter"
    if _YEAR_PATTERN.match(name):
        return "year"

    return None


def discover_files(
    data_dir: str,
) -> dict[CascadeLevel, dict[str, str]]:
    """Scan the data directory and return {level: {"path": ..., "content": ...}}.

    For levels with multiple files, the most recently modified one wins.
    """
    dirpath = Path(data_dir)
    if not dirpath.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    result: dict[CascadeLevel, dict[str, str]] = {}

    for fp in sorted(dirpath.iterdir()):
        if fp.suffix != ".md":
            continue
        level = file_to_level(fp.name)
        if level is None:
            continue

        if level not in result or fp.stat().st_mtime > Path(result[level]["path"]).stat().st_mtime:
            result[level] = {"path": str(fp), "content": fp.read_text(encoding="utf-8")}

    return result
