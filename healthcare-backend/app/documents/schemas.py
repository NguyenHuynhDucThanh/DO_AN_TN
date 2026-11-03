"""Document metadata contracts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ApprovalStatus, IngestionStatus


class DocumentCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    file_name: str = Field(min_length=1, max_length=255)
    file_type: Literal["JSON", "CSV", "PDF", "DOCX"]
    storage_key: str = Field(min_length=1, max_length=500)
    source_name: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=1000)
    checksum_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    version_number: int = Field(default=1, ge=1)


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    source_name: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=1000)


class DocumentReview(BaseModel):
    approval_status: Literal[ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    file_name: str
    file_type: str
    storage_key: str
    source_name: str | None
    source_url: str | None
    checksum_sha256: str
    version_number: int
    approval_status: ApprovalStatus
    ingestion_status: IngestionStatus
    uploaded_by: UUID
    approved_by: UUID | None
    approved_at: datetime | None
    ingestion_error: str | None
    created_at: datetime
    updated_at: datetime


class IngestionSummary(BaseModel):
    document_id: UUID
    source_format: str
    raw_records: int
    unique_contents: int
    duplicates_removed: int
    chunks_created: int
    embedded_chunks: int
    duration_seconds: float
