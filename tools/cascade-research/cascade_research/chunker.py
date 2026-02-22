from pathlib import Path
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from .config import get_chunking


def chunk_markdown(content: str, source_file: str, doc_type: str) -> list[dict]:
    """Chunk a markdown file using header-aware splitting + size enforcement."""
    chunking = get_chunking()

    # Stage 1: Split by markdown headers
    headers_to_split_on = [
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
    ]
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False,
    )
    header_chunks = header_splitter.split_text(content)

    # Stage 2: Enforce max chunk size
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunking["max_chunk_size"],
        chunk_overlap=chunking["chunk_overlap"],
        separators=["\n\n", "\n", ". ", " "],
    )

    final_chunks = []
    chunk_index = 0

    for header_chunk in header_chunks:
        metadata = header_chunk.metadata.copy()
        text = header_chunk.page_content

        # Split further if chunk exceeds max size
        if len(text) > chunking["max_chunk_size"]:
            sub_texts = text_splitter.split_text(text)
        else:
            sub_texts = [text]

        for sub_text in sub_texts:
            if not sub_text.strip():
                continue

            final_chunks.append({
                "id": f"{source_file}::{chunk_index}",
                "text": sub_text,
                "metadata": {
                    "source_file": source_file,
                    "source_dir": str(Path(source_file).parent) if "/" in source_file else "",
                    "doc_type": doc_type,
                    "h1": metadata.get("h1", ""),
                    "h2": metadata.get("h2", ""),
                    "h3": metadata.get("h3", ""),
                    "chunk_index": chunk_index,
                },
            })
            chunk_index += 1

    return final_chunks
