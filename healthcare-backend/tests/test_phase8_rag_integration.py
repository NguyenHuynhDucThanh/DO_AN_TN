"""Phase 8 ingestion governance and exact pgvector tests on PostgreSQL."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.context import ActorContext
from app.core.config import BACKEND_ROOT, get_settings
from app.core.errors import BadRequestError, ConflictError
from app.documents.ingestion import DocumentIngestionService
from app.models.enums import ApprovalStatus, IngestionStatus
from app.models.identity import Role, User, UserRole
from app.models.knowledge import Document, DocumentChunk
from app.rag.retrieval import ExactDenseRetriever

pytestmark = pytest.mark.integration


class FakeEmbeddings:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [([1.0] + [0.0] * 1023) for _ in texts]


@pytest.fixture
def phase8_session(real_database):
    connection = real_database.connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


def admin_actor(session: Session) -> ActorContext:
    user = session.scalar(
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.code == "ADMIN")
    )
    assert user is not None
    return ActorContext(user.id, frozenset({"ADMIN"}))


def create_document(
    session: Session,
    actor: ActorContext,
    file_name: str,
    status: ApprovalStatus,
) -> Document:
    source_path = BACKEND_ROOT / "data" / "rag" / "raw" / file_name
    checksum = (
        sha256(source_path.read_bytes()).hexdigest()
        if source_path.is_file()
        else uuid4().hex + uuid4().hex
    )
    document = Document(
        title="Phase 8 synthetic document",
        file_name=file_name,
        file_type="JSON",
        storage_key=f"data/rag/raw/{file_name}",
        source_name="pytest",
        checksum_sha256=checksum,
        approval_status=status,
        ingestion_status=IngestionStatus.NOT_INGESTED,
        uploaded_by=actor.user_id,
        approved_by=actor.user_id if status == ApprovalStatus.APPROVED else None,
    )
    session.add(document)
    session.commit()
    return document


def test_approved_ingestion_deduplicates_and_reingestion_replaces(phase8_session: Session) -> None:
    actor = admin_actor(phase8_session)
    file_name = f"pytest-{uuid4().hex}.jsonl"
    path = BACKEND_ROOT / "data" / "rag" / "raw" / file_name
    record = {
        "anchor": "đau họng",
        "positive": "Thông tin synthetic phục vụ kiểm thử RAG.",
        "negative": "Không được ingest",
        "meta": {"article_id": 99, "category": "test", "title": "Synthetic"},
    }
    path.write_text(json.dumps(record, ensure_ascii=False) + "\n" + json.dumps(record, ensure_ascii=False), encoding="utf-8")
    try:
        document = create_document(phase8_session, actor, file_name, ApprovalStatus.APPROVED)
        service = DocumentIngestionService(phase8_session, get_settings(), FakeEmbeddings())
        first = service.ingest(document.id, actor)
        first_count = phase8_session.scalar(
            select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == document.id)
        )
        second = service.ingest(document.id, actor)
        second_count = phase8_session.scalar(
            select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == document.id)
        )
        assert first.raw_records == 2
        assert first.unique_contents == 1
        assert first.duplicates_removed == 1
        assert first_count == second_count == first.chunks_created == second.chunks_created
        chunk = phase8_session.scalar(select(DocumentChunk).where(DocumentChunk.document_id == document.id))
        assert chunk is not None
        assert chunk.chunk_metadata["article_id"] == "99"
        assert "Không được ingest" not in chunk.content
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.parametrize("status", [ApprovalStatus.PENDING, ApprovalStatus.REJECTED])
def test_non_approved_ingestion_is_blocked(
    phase8_session: Session, status: ApprovalStatus
) -> None:
    actor = admin_actor(phase8_session)
    document = create_document(phase8_session, actor, f"blocked-{uuid4().hex}.json", status)
    with pytest.raises(ConflictError) as caught:
        DocumentIngestionService(phase8_session, get_settings(), FakeEmbeddings()).ingest(
            document.id, actor
        )
    assert caught.value.code == "document_not_approved"


def test_failed_reingestion_preserves_previous_chunks_and_marks_failed(phase8_session: Session) -> None:
    actor = admin_actor(phase8_session)
    file_name = f"failure-{uuid4().hex}.jsonl"
    path = BACKEND_ROOT / "data" / "rag" / "raw" / file_name
    path.write_text('{"positive":"Nội dung hợp lệ"}\n', encoding="utf-8")
    try:
        document = create_document(phase8_session, actor, file_name, ApprovalStatus.APPROVED)
        service = DocumentIngestionService(phase8_session, get_settings(), FakeEmbeddings())
        service.ingest(document.id, actor)
        before = phase8_session.scalar(
            select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == document.id)
        )
        path.write_text('{"positive":', encoding="utf-8")
        # Simulate an approved source whose bytes are malformed so the loader
        # failure path (not the checksum guard) is exercised.
        document.checksum_sha256 = sha256(path.read_bytes()).hexdigest()
        phase8_session.commit()
        with pytest.raises(BadRequestError):
            service.ingest(document.id, actor)
        phase8_session.expire_all()
        after = phase8_session.scalar(
            select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == document.id)
        )
        assert before == after == 1
        assert phase8_session.get(Document, document.id).ingestion_status == IngestionStatus.FAILED
    finally:
        path.unlink(missing_ok=True)


def test_ingestion_rejects_path_traversal_type_mismatch_and_oversized_file(
    phase8_session: Session,
) -> None:
    actor = admin_actor(phase8_session)
    service = DocumentIngestionService(phase8_session, get_settings(), FakeEmbeddings())

    traversal = create_document(
        phase8_session, actor, f"../outside-{uuid4().hex}.json", ApprovalStatus.APPROVED
    )
    with pytest.raises(BadRequestError) as caught:
        service.ingest(traversal.id, actor)
    assert caught.value.code == "invalid_document_path"

    mismatch_name = f"mismatch-{uuid4().hex}.csv"
    mismatch_path = BACKEND_ROOT / "data" / "rag" / "raw" / mismatch_name
    mismatch_path.write_text("content\ntext", encoding="utf-8")
    try:
        mismatch = create_document(
            phase8_session, actor, mismatch_name, ApprovalStatus.APPROVED
        )
        with pytest.raises(BadRequestError) as caught:
            service.ingest(mismatch.id, actor)
        assert caught.value.code == "document_type_mismatch"
    finally:
        mismatch_path.unlink(missing_ok=True)

    oversized_name = f"oversized-{uuid4().hex}.json"
    oversized_path = BACKEND_ROOT / "data" / "rag" / "raw" / oversized_name
    oversized_path.write_text('{"positive":"too large"}', encoding="utf-8")
    try:
        oversized = create_document(
            phase8_session, actor, oversized_name, ApprovalStatus.APPROVED
        )
        tiny_settings = get_settings().model_copy(update={"rag_max_file_bytes": 1})
        with pytest.raises(BadRequestError) as caught:
            DocumentIngestionService(
                phase8_session, tiny_settings, FakeEmbeddings()
            ).ingest(oversized.id, actor)
        assert caught.value.code == "document_too_large"
    finally:
        oversized_path.unlink(missing_ok=True)

    checksum_name = f"checksum-{uuid4().hex}.json"
    checksum_path = BACKEND_ROOT / "data" / "rag" / "raw" / checksum_name
    checksum_path.write_text('{"positive":"approved bytes"}', encoding="utf-8")
    try:
        checksum_document = create_document(
            phase8_session, actor, checksum_name, ApprovalStatus.APPROVED
        )
        checksum_document.checksum_sha256 = "0" * 64
        phase8_session.commit()
        with pytest.raises(ConflictError) as caught:
            service.ingest(checksum_document.id, actor)
        assert caught.value.code == "document_checksum_mismatch"
    finally:
        checksum_path.unlink(missing_ok=True)


def test_exact_dense_top_k_plan_ranking_sources_and_approved_only(phase8_session: Session) -> None:
    actor = admin_actor(phase8_session)
    approved = Document(
        title="Approved source",
        file_name="approved.json",
        file_type="JSON",
        storage_key="data/rag/raw/approved.json",
        source_name="approved",
        checksum_sha256=uuid4().hex + uuid4().hex,
        approval_status=ApprovalStatus.APPROVED,
        ingestion_status=IngestionStatus.COMPLETED,
        uploaded_by=actor.user_id,
        approved_by=actor.user_id,
    )
    pending = Document(
        title="Pending source",
        file_name="pending.json",
        file_type="JSON",
        storage_key="data/rag/raw/pending.json",
        source_name="pending",
        checksum_sha256=uuid4().hex + uuid4().hex,
        approval_status=ApprovalStatus.PENDING,
        ingestion_status=IngestionStatus.NOT_INGESTED,
        uploaded_by=actor.user_id,
    )
    approved.chunks.extend(
        [
            DocumentChunk(chunk_index=0, content="Gần", embedding=[1.0] + [0.0] * 1023, content_hash="a" * 64, chunk_metadata={"article_id": "near", "title": "Nguồn gần"}),
            DocumentChunk(chunk_index=1, content="Xa", embedding=[0.0, 1.0] + [0.0] * 1022, content_hash="b" * 64, chunk_metadata={"article_id": "far"}),
        ]
    )
    pending.chunks.append(
        DocumentChunk(chunk_index=0, content="Pending", embedding=[1.0] + [0.0] * 1023, content_hash="c" * 64)
    )
    phase8_session.add_all([approved, pending])
    phase8_session.commit()

    retriever = ExactDenseRetriever(phase8_session, top_k=5, max_distance=2.0)
    query = [1.0] + [0.0] * 1023
    results = retriever.retrieve(query)
    plan = retriever.explain_exact(query)
    # The development DB may already contain a real smoke corpus; the exact
    # synthetic match must rank first without assuming an otherwise empty DB.
    assert results[0].content == "Gần"
    assert results[0].distance == pytest.approx(0.0)
    assert results[0].source.article_id == "near"
    assert all(result.content != "Pending" for result in results)
    assert retriever.uses_hnsw(plan) is False
