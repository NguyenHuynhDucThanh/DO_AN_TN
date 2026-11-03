"""Document metadata persistence."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.knowledge import Document, DocumentChunk


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Document]:
        return list(self.session.scalars(select(Document).order_by(Document.created_at.desc())))

    def get(self, document_id: UUID) -> Document | None:
        return self.session.get(Document, document_id)

    def get_for_update(self, document_id: UUID) -> Document | None:
        return self.session.scalar(select(Document).where(Document.id == document_id).with_for_update())

    def add(self, document: Document) -> Document:
        self.session.add(document)
        return document

    def replace_chunks(self, document_id: UUID, chunks: list[DocumentChunk]) -> None:
        self.session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
        self.session.add_all(chunks)

    def delete_chunks(self, document_id: UUID) -> None:
        self.session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))

    def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        self.session.add_all(chunks)
