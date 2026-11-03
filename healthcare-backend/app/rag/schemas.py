"""RAG retrieval and source contracts."""

from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel


class RagSource(BaseModel):
    document_id: UUID
    title: str | None = None
    category: str | None = None
    source_name: str | None = None
    article_id: str | None = None
    page: int | None = None


@dataclass(frozen=True)
class RetrievedChunk:
    content: str
    distance: float
    source: RagSource
    chunk_id: UUID | None = None
