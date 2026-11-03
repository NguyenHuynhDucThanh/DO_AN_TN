"""Existing Document metadata/review endpoints extended with Phase 8 ingestion."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.auth.context import ActorContext
from app.auth.dependencies import get_current_actor
from app.core.database import get_db
from app.core.config import get_settings
from app.documents.embeddings import get_embedding_service
from app.documents.ingestion import DocumentIngestionService
from app.documents.schemas import DocumentCreate, DocumentRead, DocumentReview, DocumentUpdate, IngestionSummary
from app.documents.service import DocumentService
from app.core.rate_limit import enforce_rate_limit

router = APIRouter(prefix="/documents", tags=["Documents"])


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
