"""Document metadata contracts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    rejection_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_rejection_reason(self) -> "DocumentReview":
        reason = self.rejection_reason.strip() if self.rejection_reason else None
        if self.approval_status == ApprovalStatus.REJECTED and not reason:
            raise ValueError("rejection_reason is required when rejecting a document")
        self.rejection_reason = reason if self.approval_status == ApprovalStatus.REJECTED else None
        return self


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    file_name: str
    file_type: str
    storage_key: str
    source_name: str | None
    source_url: str | None
    author_name: str | None
    organization: str | None
    publication_year: int | None
    checksum_sha256: str
    mime_type: str | None
    file_size_bytes: int | None
    version_number: int
    approval_status: ApprovalStatus
    ingestion_status: IngestionStatus
    uploaded_by: UUID
    uploader_name: str
    uploader_email: str
    approved_by: UUID | None
    approved_at: datetime | None
    rejection_reason: str | None
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


class DocumentContributionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=2, max_length=255)
    source_name: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=1000)
    author_name: str | None = Field(default=None, max_length=255)
    organization: str | None = Field(default=None, max_length=255)
    publication_year: int | None = Field(default=None, ge=1800)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 2:
            raise ValueError("title must contain at least 2 non-whitespace characters")
        return stripped

    @field_validator("source_name", "source_url", "author_name", "organization")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("publication_year")
    @classmethod
    def validate_publication_year(cls, value: int | None) -> int | None:
        if value is not None and value > datetime.now().year + 1:
            raise ValueError("publication_year cannot be later than next year")
        return value


class DocumentContributionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    source_name: str | None = Field(default=None, max_length=255)
    source_url: str | None = Field(default=None, max_length=1000)
    author_name: str | None = Field(default=None, max_length=255)
    organization: str | None = Field(default=None, max_length=255)
    publication_year: int | None = Field(default=None, ge=1800)

    @field_validator("title")
    @classmethod
    def strip_update_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if len(stripped) < 2:
            raise ValueError("title must contain at least 2 non-whitespace characters")
        return stripped

    @field_validator("source_name", "source_url", "author_name", "organization")
    @classmethod
    def strip_update_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("publication_year")
    @classmethod
    def validate_update_publication_year(cls, value: int | None) -> int | None:
        if value is not None and value > datetime.now().year + 1:
            raise ValueError("publication_year cannot be later than next year")
        return value


class DocumentContributionRead(BaseModel):
    """Doctor-safe view: internal storage key and full checksum are deliberately absent."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    file_name: str
    file_type: str
    source_name: str | None
    source_url: str | None
    author_name: str | None
    organization: str | None
    publication_year: int | None
    mime_type: str | None
    file_size_bytes: int | None
    approval_status: ApprovalStatus
    ingestion_status: IngestionStatus
    uploaded_by: UUID
    approved_at: datetime | None
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime
