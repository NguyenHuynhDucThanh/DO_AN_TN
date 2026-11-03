"""Paragraph-aware chunking and deterministic content hashing."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from app.documents.loaders import NormalizedSource, normalize_text


@dataclass(frozen=True)
class PreparedChunk:
    content: str
    content_hash: str
    page_number: int | None
    section: str | None
    metadata: dict[str, Any]


def content_hash(content: str) -> str:
    return sha256(normalize_text(content).encode("utf-8")).hexdigest()


def chunk_source(source: NormalizedSource, *, max_chars: int, overlap_chars: int) -> list[PreparedChunk]:
    paragraphs = [paragraph for paragraph in source.content.split("\n") if paragraph.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            step = max_chars - overlap_chars
            chunks.extend(paragraph[start : start + max_chars] for start in range(0, len(paragraph), step))
            continue
        candidate = paragraph if not current else f"{current}\n{paragraph}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            chunks.append(current)
            tail = current[-overlap_chars:] if overlap_chars else ""
            current = f"{tail}\n{paragraph}".strip()
    if current:
        chunks.append(current)

    base_metadata = {
        "source_type": source.source_type,
        "source_name": source.source_name,
        **source.metadata,
    }
    optional = {
        "article_id": source.external_id,
        "category": source.category,
        "title": source.title,
    }
    base_metadata.update({key: value for key, value in optional.items() if value is not None})
    return [
        PreparedChunk(
            content=chunk,
            content_hash=content_hash(chunk),
            page_number=source.page_number,
            section=source.section,
            metadata=base_metadata,
        )
        for chunk in chunks
        if chunk
    ]
