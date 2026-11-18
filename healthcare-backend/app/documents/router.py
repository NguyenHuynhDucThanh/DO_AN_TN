"""Existing Document metadata/review endpoints extended with Phase 8 ingestion."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.context import ActorContext
from app.auth.dependencies import get_current_actor
from app.core.database import get_db
from app.core.config import get_settings
from app.documents.embeddings import get_embedding_service
from app.documents.ingestion import DocumentIngestionService
from app.documents.schemas import (
    DocumentContributionCreate,
    DocumentContributionRead,
    DocumentContributionUpdate,
    DocumentCreate,
    DocumentRead,
    DocumentReview,
    DocumentUpdate,
    IngestionSummary,
)
from app.documents.service import DocumentService
from app.documents.storage import DocumentUploadStorage
from app.core.rate_limit import enforce_rate_limit
from app.core.errors import BadRequestError

router = APIRouter(prefix="/documents", tags=["Documents"])


def parse_document_contribution_form(
    title: Annotated[str, Form(min_length=2, max_length=255)],
    source_name: Annotated[str | None, Form(max_length=255)] = None,
    source_url: Annotated[str | None, Form(max_length=1000)] = None,
    author_name: Annotated[str | None, Form(max_length=255)] = None,
    organization: Annotated[str | None, Form(max_length=255)] = None,
    publication_year: Annotated[int | None, Form(ge=1800)] = None,
) -> DocumentContributionCreate:
    try:
        return DocumentContributionCreate(
            title=title,
            source_name=source_name,
            source_url=source_url,
            author_name=author_name,
            organization=organization,
            publication_year=publication_year,
        )
    except ValueError as exc:
        raise BadRequestError(
            "Document contribution metadata is invalid.",
            "invalid_document_metadata",
        ) from exc


@router.post(
    "/contributions",
    response_model=DocumentContributionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_document_contribution(
    data: Annotated[DocumentContributionCreate, Depends(parse_document_contribution_form)],
    file: Annotated[UploadFile, File(description="PDF, DOCX, CSV, JSON or JSONL knowledge file")],
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
) -> DocumentContributionRead:
    actor.require_any_role("DOCTOR", "ADMIN")
    storage = DocumentUploadStorage(get_settings())
    try:
        prepared = await storage.prepare(file)
        document = DocumentService(db).create_contribution(data, prepared, actor)
        return DocumentContributionRead.model_validate(document)
    finally:
        await file.close()


@router.get("/contributions/me", response_model=list[DocumentContributionRead])
def list_own_document_contributions(
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return DocumentService(db).list_own_contributions(actor)


@router.get("/contributions/{document_id}", response_model=DocumentContributionRead)
def get_document_contribution(
    document_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return DocumentService(db).get_contribution(document_id, actor)


@router.patch("/contributions/{document_id}", response_model=DocumentContributionRead)
def update_document_contribution(
    document_id: UUID,
    data: DocumentContributionUpdate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return DocumentService(db).update_contribution(document_id, data, actor)


@router.get("", response_model=list[DocumentRead])
def list_documents(
    db: Annotated[Session, Depends(get_db)], actor: Annotated[ActorContext, Depends(get_current_actor)]
):
    return DocumentService(db).list(actor)


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(
    document_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return DocumentService(db).get(document_id, actor)


@router.get("/{document_id}/file", response_class=FileResponse)
def download_document_file(
    document_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
) -> FileResponse:
    actor.require_any_role("ADMIN")
    document = DocumentService(db).get(document_id, actor)
    path = DocumentUploadStorage.resolve_existing(document.storage_key)
    safe_name = document.file_name.replace("\r", "").replace("\n", "")
    return FileResponse(
        path,
        media_type=document.mime_type or "application/octet-stream",
        filename=safe_name,
    )


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_document(
    data: DocumentCreate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return DocumentService(db).create(data, actor)


@router.patch("/{document_id}", response_model=DocumentRead)
def update_document(
    document_id: UUID,
    data: DocumentUpdate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return DocumentService(db).update(document_id, data, actor)


@router.post("/{document_id}/review", response_model=DocumentRead)
def review_document(
    document_id: UUID,
    data: DocumentReview,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return DocumentService(db).review(document_id, data, actor)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
) -> Response:
    DocumentService(db).delete(document_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{document_id}/ingest", response_model=IngestionSummary)
def ingest_document(
    document_id: UUID,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
) -> IngestionSummary:
    settings = get_settings()
    enforce_rate_limit(
        request,
        scope="document_ingestion",
        identity=str(actor.user_id),
        limit=settings.ingestion_rate_limit,
        window_seconds=settings.common_rate_window_seconds,
        enabled=settings.rate_limit_enabled,
    )
    embeddings = get_embedding_service()
    return DocumentIngestionService(db, settings, embeddings).ingest(document_id, actor)
