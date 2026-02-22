import hashlib
import fnmatch
from pathlib import Path
from datetime import datetime


def file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def file_modified_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat()


def should_include(filepath: Path, dir_config: dict, dir_root: Path) -> bool:
    """Check if a file should be included based on directory config."""
    rel_path = str(filepath.relative_to(dir_root))

    # Exclude patterns
    for pattern in dir_config.get("exclude", []):
        if fnmatch.fnmatch(rel_path, pattern):
            return False
        if fnmatch.fnmatch(filepath.name, pattern):
            return False
        # Match directory prefix (e.g. exclude "product-research" matches "product-research/foo.md")
        if rel_path.startswith(pattern + "/"):
            return False

    # Only include .md files if flagged
    if dir_config.get("include_only_md", False):
        if filepath.suffix != ".md":
            return False

    return True


def collect_files(root: Path, directories: list[dict]) -> list[tuple[Path, str]]:
    """Collect all markdown files from configured directories.

    Returns list of (absolute_path, doc_type) tuples.
    """
    files = []
    seen = set()

    for dir_config in directories:
        dir_path = root / dir_config["path"]
        if not dir_path.exists():
            continue

        doc_type = dir_config.get("doc_type", "unknown")

        for md_file in sorted(dir_path.rglob("*.md")):
            if md_file in seen:
                continue
            if should_include(md_file, dir_config, dir_path):
                files.append((md_file, doc_type))
                seen.add(md_file)

    return files
