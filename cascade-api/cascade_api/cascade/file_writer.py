"""Backup and write cascade files with rollback support."""

from __future__ import annotations

import shutil
from pathlib import Path


def _backup_dir(data_dir: str, thread_id: str) -> Path:
    """Resolve the backup directory for a given thread under data_dir/backups/."""
    return Path(data_dir) / "backups" / thread_id


def backup_file(file_path: str, thread_id: str, data_dir: str) -> None:
    """Backup *file_path* before overwriting. First backup wins (no overwrite)."""
    bdir = _backup_dir(data_dir, thread_id)
    bdir.mkdir(parents=True, exist_ok=True)

    backup_path = bdir / Path(file_path).name
    if not backup_path.exists():
        shutil.copy2(file_path, backup_path)


def write_cascade_file(
    file_path: str, content: str, thread_id: str, data_dir: str
) -> None:
    """Write new content to a cascade file, creating a backup first."""
    backup_file(file_path, thread_id, data_dir)
    Path(file_path).write_text(content, encoding="utf-8")


def restore_backups(thread_id: str, data_dir: str) -> list[str]:
    """Return a list of backup file paths for *thread_id* (rollback support)."""
    bdir = _backup_dir(data_dir, thread_id)
    if not bdir.exists():
        return []
    return [str(p) for p in bdir.iterdir()]


def cleanup_backups(thread_id: str, data_dir: str) -> None:
    """Remove the backup directory for a completed/cancelled thread."""
    bdir = _backup_dir(data_dir, thread_id)
    if bdir.exists():
        shutil.rmtree(bdir)
