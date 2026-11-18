"""Document metadata and approval rules; no ingestion or embedding."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.context import ActorContext
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.documents.repository import DocumentRepository
from app.documents.schemas import (
    DocumentContributionCreate,
    DocumentContributionUpdate,
    DocumentCreate,
    DocumentReview,
    DocumentUpdate,
)
from app.documents.storage import PreparedDocumentUpload
from app.models.enums import ApprovalStatus, IngestionStatus
from app.models.knowledge import Document
from app.models.operations import AuditLog


class DocumentService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DocumentRepository(session)

    def list(self, actor: ActorContext) -> list[Document]:
        actor.require_any_role("STAFF", "ADMIN")
        return self.repository.list()

    def get(self, document_id: UUID, actor: ActorContext) -> Document:
        actor.require_any_role("STAFF", "ADMIN")
        document = self.repository.get(document_id)
        if document is None:
            raise NotFoundError("Document was not found.", "document_not_found")
        return document

    def create(self, data: DocumentCreate, actor: ActorContext) -> Document:
        actor.require_any_role("STAFF", "ADMIN")
        payload = data.model_dump()
        payload["checksum_sha256"] = data.checksum_sha256.lower()
        document = Document(
            **payload,
            uploaded_by=actor.user_id,
            approval_status=ApprovalStatus.PENDING,
            ingestion_status=IngestionStatus.NOT_INGESTED,
        )
        self.repository.add(document)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError(
                "A document with the same content already exists.",
                "document_content_exists",
            ) from exc
        self.session.refresh(document)
        return document

    def create_contribution(
        self,
        data: DocumentContributionCreate,
        prepared: PreparedDocumentUpload,
        actor: ActorContext,
    ) -> Document:
        actor.require_any_role("DOCTOR", "ADMIN")
        if self.repository.get_by_checksum(prepared.checksum_sha256) is not None:
            prepared.cleanup()
            raise ConflictError(
                "A document with the same content already exists in the system.",
                "document_content_exists",
            )
        document = Document(
            **data.model_dump(),
            file_name=prepared.original_filename,
            file_type=prepared.file_type,
            storage_key=prepared.storage_key,
            checksum_sha256=prepared.checksum_sha256,
            mime_type=prepared.mime_type,
            file_size_bytes=prepared.file_size_bytes,
            uploaded_by=actor.user_id,
            approval_status=ApprovalStatus.PENDING,
            ingestion_status=IngestionStatus.NOT_INGESTED,
        )
        self.repository.add(document)
        try:
            self.session.flush()
            prepared.finalize()
            self.session.add(
                AuditLog(
                    actor_user_id=actor.user_id,
                    action="DOCUMENT_CONTRIBUTED",
                    entity_type="document",
                    entity_id=document.id,
                    audit_metadata={
                        "file_type": document.file_type,
                        "file_size_bytes": document.file_size_bytes,
                        "checksum_prefix": document.checksum_sha256[:12],
                    },
                )
            )
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            prepared.cleanup()
            raise ConflictError(
                "A document with the same content already exists in the system.",
                "document_content_exists",
            ) from exc
        except Exception:
            self.session.rollback()
            prepared.cleanup()
            raise
        self.session.refresh(document)
        return document

    def list_own_contributions(self, actor: ActorContext) -> list[Document]:
        actor.require_any_role("DOCTOR", "ADMIN")
        return self.repository.list_by_uploader(actor.user_id)

    def get_contribution(self, document_id: UUID, actor: ActorContext) -> Document:
        actor.require_any_role("DOCTOR", "ADMIN")
        document = self.repository.get(document_id)
        if document is None:
            raise NotFoundError("Document contribution was not found.", "document_not_found")
        if not actor.has_any_role("ADMIN") and document.uploaded_by != actor.user_id:
            raise ForbiddenError()
        return document

    def update_contribution(
        self, document_id: UUID, data: DocumentContributionUpdate, actor: ActorContext
    ) -> Document:
        document = self.get_contribution(document_id, actor)
        if document.approval_status not in {ApprovalStatus.PENDING, ApprovalStatus.REJECTED}:
            raise ConflictError(
                "Approved document content cannot be changed without a new review.",
                "document_reviewed",
            )
        if document.ingestion_status != IngestionStatus.NOT_INGESTED:
            raise ConflictError("An ingested document cannot be edited.", "document_ingested")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(document, field, value)
        if document.approval_status == ApprovalStatus.REJECTED:
            document.approval_status = ApprovalStatus.PENDING
            document.ingestion_status = IngestionStatus.NOT_INGESTED
            document.approved_by = None
            document.approved_at = None
            document.rejection_reason = None
            action = "DOCUMENT_RESUBMITTED"
        else:
            action = "DOCUMENT_CONTRIBUTION_UPDATED"
        self.session.add(
            AuditLog(
                actor_user_id=actor.user_id,
                action=action,
                entity_type="document",
                entity_id=document.id,
                audit_metadata={"approval_status": document.approval_status.value},
            )
        )
        self.session.commit()
        self.session.refresh(document)
        return document

    def update(self, document_id: UUID, data: DocumentUpdate, actor: ActorContext) -> Document:
        document = self.get(document_id, actor)
        if not actor.has_any_role("ADMIN") and document.uploaded_by != actor.user_id:
            raise ForbiddenError()
        if document.approval_status != ApprovalStatus.PENDING:
            raise ConflictError("Reviewed document metadata cannot be changed.", "document_reviewed")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(document, field, value.strip() if isinstance(value, str) else value)
        self.session.commit()
        self.session.refresh(document)
        return document

    def review(self, document_id: UUID, data: DocumentReview, actor: ActorContext) -> Document:
        actor.require_any_role("ADMIN")
        document = self.repository.get(document_id)
        if document is None:
            raise NotFoundError("Document was not found.", "document_not_found")
        if document.ingestion_status != IngestionStatus.NOT_INGESTED:
            raise ConflictError("An ingested document cannot be re-reviewed here.", "document_ingested")
        document.approval_status = data.approval_status
        document.approved_by = actor.user_id
        document.approved_at = datetime.now(timezone.utc)
        document.rejection_reason = data.rejection_reason
        self.session.add(
            AuditLog(
                actor_user_id=actor.user_id,
                action=f"DOCUMENT_{data.approval_status.value}",
                entity_type="document",
                entity_id=document.id,
                audit_metadata={"approval_status": data.approval_status.value},
            )
        )
        self.session.commit()
        self.session.refresh(document)
        return document

    def delete(self, document_id: UUID, actor: ActorContext) -> None:
        actor.require_any_role("ADMIN")
        document = self.repository.get(document_id)
        if document is None:
            raise NotFoundError("Document was not found.", "document_not_found")
        if (
            document.approval_status != ApprovalStatus.PENDING
            or document.ingestion_status != IngestionStatus.NOT_INGESTED
            or document.chunks
        ):
            raise ConflictError(
                "Only pending, non-ingested metadata without chunks can be deleted.",
                "document_delete_forbidden",
            )
        document_id_value = document.id
        self.session.delete(document)
        self.session.add(
            AuditLog(
                actor_user_id=actor.user_id,
                action="DOCUMENT_METADATA_DELETED",
                entity_type="document",
                entity_id=document_id_value,
                audit_metadata={"approval_status": ApprovalStatus.PENDING.value},
            )
        )
        self.session.commit()
