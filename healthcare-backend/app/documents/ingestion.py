"""APPROVED-only, deterministic ingestion for the existing Document model."""

from __future__ import annotations

import time
from collections.abc import Callable
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.context import ActorContext
from app.core.config import BACKEND_ROOT, Settings
from app.core.errors import ApplicationError, BadRequestError, ConflictError, NotFoundError
from app.documents.chunking import chunk_source, content_hash
from app.documents.embeddings import EmbeddingError, EmbeddingService
from app.documents.loaders import DocumentLoadError, load_sources
from app.documents.repository import DocumentRepository
from app.documents.schemas import IngestionSummary
from app.models.enums import ApprovalStatus, IngestionStatus
from app.models.knowledge import DocumentChunk
from app.models.operations import AuditLog

EXTENSIONS = {
    "JSON": {".json", ".jsonl"},
    "CSV": {".csv"},
    "PDF": {".pdf"},
    "DOCX": {".docx"},
}


def file_checksum(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class DocumentIngestionService:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.repository = DocumentRepository(session)
        self.embedding_service = embedding_service or EmbeddingService(
            settings.embedding_model, settings.embedding_batch_size
        )

    def _resolve_source(self, storage_key: str, source_override: Path | None = None) -> Path:
        raw_root = (BACKEND_ROOT / "data" / "rag" / "raw").resolve()
        candidate = source_override or Path(storage_key)
        if not candidate.is_absolute():
            candidate = BACKEND_ROOT / candidate
        path = candidate.resolve()
        if not path.is_relative_to(raw_root):
            raise BadRequestError("Document path is outside the RAG raw directory.", "invalid_document_path")
        if not path.is_file():
            raise NotFoundError("Document source file was not found.", "document_file_not_found")
        if path.stat().st_size > self.settings.rag_max_file_bytes:
            raise BadRequestError("Document exceeds the configured ingestion size limit.", "document_too_large")
        return path

    def ingest(
        self,
        document_id: UUID,
        actor: ActorContext,
        *,
        source_override: Path | None = None,
        limit: int | None = None,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> IngestionSummary:
        actor.require_any_role("ADMIN")
        document = self.repository.get_for_update(document_id)
        if document is None:
            raise NotFoundError("Document was not found.", "document_not_found")
        if document.approval_status != ApprovalStatus.APPROVED:
            raise ConflictError("Only APPROVED documents can be ingested.", "document_not_approved")
        file_type = document.file_type.upper()
        path = self._resolve_source(document.storage_key, source_override)
        if path.suffix.lower() not in EXTENSIONS.get(file_type, set()):
            raise BadRequestError("File extension does not match document type.", "document_type_mismatch")
        if file_checksum(path) != document.checksum_sha256.lower():
            raise ConflictError(
                "Document source checksum does not match its approved metadata.",
                "document_checksum_mismatch",
            )

        started = time.perf_counter()
        document.ingestion_status = IngestionStatus.PROCESSING
        document.ingestion_error = None
        self.session.commit()

        raw_records = unique_contents = duplicates_removed = 0
        pending = []
        chunk_index = 0
        seen_content: set[str] = set()
        try:
            document = self.repository.get_for_update(document_id)
            if document is None:
                raise NotFoundError("Document was not found.", "document_not_found")
            self.repository.delete_chunks(document.id)
            for source in load_sources(path, file_type, limit=limit):
                raw_records += 1
                source_hash = content_hash(source.content)
                if source_hash in seen_content:
                    duplicates_removed += 1
                    continue
                seen_content.add(source_hash)
                unique_contents += 1
                for item in chunk_source(
                    source,
                    max_chars=self.settings.rag_chunk_max_chars,
                    overlap_chars=self.settings.rag_chunk_overlap_chars,
                ):
                    pending.append(item)
                    if len(pending) >= self.settings.embedding_batch_size:
                        chunk_index = self._embed_and_add(document.id, pending, chunk_index)
                        pending = []
                if progress_callback is not None and raw_records % 1000 == 0:
                    progress_callback(raw_records, chunk_index)
            if pending:
                chunk_index = self._embed_and_add(document.id, pending, chunk_index)
            if progress_callback is not None:
                progress_callback(raw_records, chunk_index)
            if chunk_index == 0:
                raise DocumentLoadError("Document contains no usable content.", "empty_document")
            document.ingestion_status = IngestionStatus.COMPLETED
            document.ingestion_error = None
            self.session.add(
                AuditLog(
                    actor_user_id=actor.user_id,
                    action="DOCUMENT_INGESTED",
                    entity_type="document",
                    entity_id=document.id,
                    audit_metadata={
                        "source_format": file_type,
                        "raw_records": raw_records,
                        "unique_contents": unique_contents,
                        "duplicates_removed": duplicates_removed,
                        "chunks_created": chunk_index,
                    },
                )
            )
            self.session.commit()
        except (DocumentLoadError, EmbeddingError) as exc:
            self.session.rollback()
            failed = self.repository.get(document_id)
            if failed is not None:
                failed.ingestion_status = IngestionStatus.FAILED
                failed.ingestion_error = str(exc)[:1000]
                self.session.commit()
            if isinstance(exc, DocumentLoadError):
                raise BadRequestError(str(exc), exc.code) from exc
            raise ApplicationError(503, "embedding_unavailable", "Embedding service is unavailable.") from exc
        except Exception:
            self.session.rollback()
            failed = self.repository.get(document_id)
            if failed is not None:
                failed.ingestion_status = IngestionStatus.FAILED
                failed.ingestion_error = "Ingestion failed."
                self.session.commit()
            raise

        return IngestionSummary(
            document_id=document_id,
            source_format=file_type,
            raw_records=raw_records,
            unique_contents=unique_contents,
            duplicates_removed=duplicates_removed,
            chunks_created=chunk_index,
            embedded_chunks=chunk_index,
            duration_seconds=round(time.perf_counter() - started, 3),
        )

    def _embed_and_add(self, document_id: UUID, prepared: list, start_index: int) -> int:
        embeddings = self.embedding_service.embed([chunk.content for chunk in prepared])
        chunks = [
            DocumentChunk(
                document_id=document_id,
                chunk_index=start_index + offset,
                content=item.content,
                embedding=embedding,
                page_number=item.page_number,
                section=item.section,
                chunk_metadata=item.metadata,
                content_hash=item.content_hash,
            )
            for offset, (item, embedding) in enumerate(zip(prepared, embeddings, strict=True))
        ]
        self.repository.add_chunks(chunks)
        self.session.flush()
        return start_index + len(chunks)
