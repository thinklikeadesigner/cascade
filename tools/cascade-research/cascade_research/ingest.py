import re
import chromadb
from pathlib import Path
from rich.console import Console
from rich.table import Table

from .config import get_storage_path, get_collection_name, get_project_root, get_directories
from .chunker import chunk_markdown
from .utils import collect_files, file_modified_iso

console = Console()

# Patterns that indicate ASCII art diagrams
ASCII_ART_PATTERNS = [
    re.compile(r"[│├└┌┐┘┤┬┴┼─]{3,}"),     # Box-drawing characters
    re.compile(r"[\+\-\|]{3,}.*[\+\-\|]"),   # +---+---+ style
    re.compile(r"[→←↑↓↔]{2,}"),              # Arrow characters
    re.compile(r"\s{2,}──►\s"),               # ASCII arrows
    re.compile(r"\|\s+\|.*\|\s+\|"),          # | col | col | without markdown table
]


def _check_ascii_art(content: str, filepath: str) -> list[str]:
    """Check file for ASCII art diagrams that should be Mermaid."""
    warnings = []
    for i, line in enumerate(content.splitlines(), 1):
        for pattern in ASCII_ART_PATTERNS:
            if pattern.search(line):
                warnings.append(f"  {filepath}:{i} — possible ASCII diagram (use Mermaid instead)")
                break
    return warnings


def get_client():
    storage_path = get_storage_path()
    storage_path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(storage_path))


def get_collection(client=None):
    if client is None:
        client = get_client()
    return client.get_or_create_collection(
        name=get_collection_name(),
        metadata={"hnsw:space": "cosine"},
    )


def ingest_file(collection, filepath: Path, doc_type: str, root: Path):
    """Ingest a single file. Returns (chunk_count, status)."""
    rel_path = str(filepath.relative_to(root))
    content = filepath.read_text(encoding="utf-8")
    modified = file_modified_iso(filepath)

    # Check if already indexed and unchanged
    existing = collection.get(
        where={"source_file": rel_path},
        include=["metadatas"],
    )

    if existing["ids"]:
        stored_modified = existing["metadatas"][0].get("file_modified", "")
        if stored_modified == modified:
            return 0, "skipped"
        # File changed — delete old chunks
        collection.delete(ids=existing["ids"])

    # Chunk the file
    chunks = chunk_markdown(content, rel_path, doc_type)

    if not chunks:
        return 0, "empty"

    # Tag all chunks with file modification time
    for chunk in chunks:
        chunk["metadata"]["file_modified"] = modified

    # Add to collection
    collection.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[c["metadata"] for c in chunks],
    )

    return len(chunks), "indexed"


def ingest_all(force: bool = False):
    """Ingest all configured directories."""
    root = get_project_root()
    directories = get_directories()
    files = collect_files(root, directories)

    client = get_client()

    if force:
        try:
            client.delete_collection(get_collection_name())
        except Exception:
            pass

    collection = get_collection(client)

    table = Table(title="Ingestion Results")
    table.add_column("File", style="cyan")
    table.add_column("Chunks", justify="right", style="green")
    table.add_column("Status", style="yellow")

    total_chunks = 0
    indexed = 0
    skipped = 0

    for filepath, doc_type in files:
        rel_path = str(filepath.relative_to(root))
        try:
            count, status = ingest_file(collection, filepath, doc_type, root)
        except Exception as e:
            table.add_row(rel_path, "0", f"[red]error: {e}[/red]")
            continue

        table.add_row(rel_path, str(count), status)
        total_chunks += count
        if status == "indexed":
            indexed += 1
        elif status == "skipped":
            skipped += 1

    console.print(table)
    console.print(
        f"\n[bold]Total:[/bold] {len(files)} files scanned, "
        f"{indexed} indexed ({total_chunks} chunks), {skipped} unchanged"
    )

    # Check for ASCII art violations
    ascii_warnings = []
    for filepath, doc_type in files:
        content = filepath.read_text(encoding="utf-8")
        rel_path = str(filepath.relative_to(root))
        ascii_warnings.extend(_check_ascii_art(content, rel_path))

    if ascii_warnings:
        # Dedupe to max 3 per file
        by_file = {}
        for w in ascii_warnings:
            f = w.split(":")[0].strip()
            by_file.setdefault(f, []).append(w)

        console.print(f"\n[yellow bold]ASCII art detected in {len(by_file)} files (should be Mermaid):[/yellow bold]")
        for f, warns in by_file.items():
            for w in warns[:3]:
                console.print(f"[yellow]{w}[/yellow]")
            if len(warns) > 3:
                console.print(f"[dim]  ...and {len(warns) - 3} more in {f}[/dim]")

    return total_chunks


def ingest_single(filepath_str: str):
    """Ingest a single file."""
    root = get_project_root()
    filepath = Path(filepath_str)

    if not filepath.is_absolute():
        filepath = root / filepath

    if not filepath.exists():
        console.print(f"[red]File not found:[/red] {filepath}")
        return

    # Determine doc_type from path
    rel_path = filepath.relative_to(root)
    doc_type = "unknown"
    directories = get_directories()
    for dir_config in directories:
        if str(rel_path).startswith(dir_config["path"]):
            doc_type = dir_config.get("doc_type", "unknown")
            break

    collection = get_collection()
    count, status = ingest_file(collection, filepath, doc_type, root)
    console.print(f"[bold]{rel_path}:[/bold] {count} chunks ({status})")
