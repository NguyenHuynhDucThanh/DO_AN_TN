"""Approved knowledge documents and pgvector-backed chunks."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import ApprovalStatus, IngestionStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

EMBEDDING_DIMENSION = 1024


def enum_type(enum_class: type, name: str, length: int = 32) -> Enum:
    return Enum(enum_class, name=name, native_enum=False, create_constraint=True, length=length)


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint("version_number > 0", name="positive_version"),
        CheckConstraint("file_type IN ('JSON', 'CSV', 'PDF', 'DOCX')", name="supported_file_type"),
        CheckConstraint(
            "ingestion_status = 'NOT_INGESTED' OR approval_status = 'APPROVED'",
            name="ingestion_requires_approval",
        ),
        UniqueConstraint("checksum_sha256", "version_number", name="uq_documents_checksum_version"),
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(255))
    source_url: Mapped[str | None] = mapped_column(String(1000))
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    approval_status: Mapped[ApprovalStatus] = mapped_column(
        enum_type(ApprovalStatus, "approval_status", 16), nullable=False,
        default=ApprovalStatus.PENDING, server_default=ApprovalStatus.PENDING.value,
    )
    ingestion_status: Mapped[IngestionStatus] = mapped_column(
        enum_type(IngestionStatus, "ingestion_status", 20), nullable=False,
        default=IngestionStatus.NOT_INGESTED, server_default=IngestionStatus.NOT_INGESTED.value,
    )
    uploaded_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    approved_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ingestion_error: Mapped[str | None] = mapped_column(String(1000))

    chunks: Mapped[list[DocumentChunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="DocumentChunk.chunk_index"
    )


class DocumentChunk(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        CheckConstraint("chunk_index >= 0", name="non_negative_chunk_index"),
        CheckConstraint("page_number IS NULL OR page_number > 0", name="positive_page_number"),
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_document_index"),
        Index(
            "ix_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSION), nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    section: Mapped[str | None] = mapped_column(String(255))
    chunk_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict, server_default="{}")
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    document: Mapped[Document] = relationship(back_populates="chunks")
