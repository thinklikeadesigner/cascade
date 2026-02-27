"""Read cascade files from the data directory."""

from __future__ import annotations

from pathlib import Path

from cascade_api.cascade.level_utils import CascadeLevel, discover_files


def read_cascade_files(data_dir: str) -> dict[CascadeLevel, dict[str, str]]:
    """Read all cascade files from *data_dir*, mapped by level."""
    return discover_files(data_dir)


def read_file_content(file_path: str) -> str:
    """Read a single file's current content (used for conflict detection)."""
    return Path(file_path).read_text(encoding="utf-8")
