"""KB-001B schema, secure upload, ownership, cleanup and isolation tests."""

from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import Path
import shutil
from uuid import uuid4

import pymupdf
import pytest
from docx import Document as DocxDocument
from fastapi import UploadFile
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.context import ActorContext
from app.auth.dependencies import get_current_actor
from app.core.config import BACKEND_ROOT, get_settings
from app.core.database import get_db
from app.core.errors import BadRequestError, PayloadTooLargeError
from app.documents.schemas import DocumentContributionCreate, DocumentContributionUpdate
from app.documents.service import DocumentService
from app.documents.storage import DocumentUploadStorage
from app.main import create_app
from app.models.enums import ApprovalStatus, IngestionStatus, UserStatus
from app.models.identity import Role, User, UserRole
from app.models.knowledge import Document

pytestmark = pytest.mark.integration


def _upload(name: str, payload: bytes, content_type: str = "application/octet-stream") -> UploadFile:
    return UploadFile(file=BytesIO(payload), filename=name, headers={"content-type": content_type})


def _pdf_bytes() -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Synthetic medical knowledge for upload testing.")
    payload = document.tobytes()
    document.close()
    return payload


def _docx_bytes() -> bytes:
    stream = BytesIO()
    document = DocxDocument()
    document.add_heading("Synthetic knowledge", level=1)
    document.add_paragraph("Nội dung y khoa tổng hợp phục vụ kiểm thử.")
    document.save(stream)
    return stream.getvalue()


VALID_FILES = {
    "knowledge.pdf": _pdf_bytes(),
    "knowledge.docx": _docx_bytes(),
    "knowledge.csv": "content,title\nNội dung tổng hợp,Kiểm thử\n".encode("utf-8"),
    "knowledge.json": '{"content":"Nội dung tổng hợp"}'.encode(),
    "knowledge.jsonl": b'{"content":"Dong thu nhat"}\n{"content":"Dong thu hai"}\n',
}


@pytest.fixture
def kb_session(real_database):
    connection = real_database.connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


def _actor(session: Session, role_code: str) -> ActorContext:
    role = session.scalar(select(Role).where(Role.code == role_code))
    assert role is not None
    user = User(
        email=f"kb-{role_code.lower()}-{uuid4().hex}@example.invalid",
        password_hash="!synthetic-no-login",
        full_name=f"KB {role_code} Synthetic",
        phone="0900000099",
        status=UserStatus.ACTIVE,
    )
    session.add(user)
    session.flush()
    session.add(UserRole(user_id=user.id, role_id=role.id))
    session.commit()
    return ActorContext(user.id, frozenset({role_code}))


@pytest.fixture
def actors(kb_session: Session) -> dict[str, ActorContext]:
    return {
        "doctor": _actor(kb_session, "DOCTOR"),
        "other_doctor": _actor(kb_session, "DOCTOR"),
        "admin": _actor(kb_session, "ADMIN"),
        "staff": _actor(kb_session, "STAFF"),
        "patient": _actor(kb_session, "PATIENT"),
    }


@pytest.fixture
def upload_root(monkeypatch: pytest.MonkeyPatch) -> Path:
    relative = f"data/rag/raw/uploads/pytest-{uuid4().hex}"
    root = BACKEND_ROOT / relative
    monkeypatch.setenv("DOCUMENT_UPLOAD_ROOT", relative)
    monkeypatch.setenv("DOCUMENT_UPLOAD_MAX_BYTES", "25000000")
    get_settings.cache_clear()
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)
        get_settings.cache_clear()


@pytest.mark.anyio
@pytest.mark.parametrize("filename", list(VALID_FILES))
async def test_storage_accepts_supported_formats_and_generates_safe_name(
    filename: str, upload_root: Path
) -> None:
    storage = DocumentUploadStorage(get_settings())
    payload = VALID_FILES[filename]
    prepared = await storage.prepare(_upload(filename, payload))
    try:
        assert prepared.original_filename == filename
        assert prepared.file_size_bytes == len(payload)
        assert prepared.checksum_sha256 == sha256(payload).hexdigest()
        assert prepared.final_path.parent == upload_root.resolve()
        assert prepared.final_path.name != filename
        assert prepared.storage_key.startswith("data/rag/raw/uploads/")
        assert not Path(prepared.storage_key).is_absolute()
        prepared.finalize()
        assert prepared.final_path.is_file()
    finally:
        prepared.cleanup()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("filename", "payload", "error_code"),
    [
        ("empty.json", b"", "empty_document"),
        ("knowledge.txt", b"content", "unsupported_document_format"),
        ("fake.pdf", b"not a pdf", "invalid_document_content"),
        ("bad.docx", b"not a zip", "invalid_document_content"),
        ("bad.csv", b"unsupported\nvalue\n", "missing_content_field"),
        ("bad.json", b'{"content":', "invalid_json"),
        ("../escape.json", b'{"content":"x"}', "invalid_document_filename"),
        ("..\\escape.json", b'{"content":"x"}', "invalid_document_filename"),
    ],
)
async def test_storage_rejects_invalid_files_without_orphans(
    filename: str, payload: bytes, error_code: str, upload_root: Path
) -> None:
    storage = DocumentUploadStorage(get_settings())
    with pytest.raises(BadRequestError) as caught:
        await storage.prepare(_upload(filename, payload))
    assert caught.value.code == error_code
    assert not list(upload_root.glob("*"))


@pytest.mark.anyio
async def test_storage_stops_at_hard_size_limit_and_cleans_temp(upload_root: Path) -> None:
    settings = get_settings().model_copy(update={"document_upload_max_bytes": 8})
    storage = DocumentUploadStorage(settings)
    with pytest.raises(PayloadTooLargeError):
        await storage.prepare(_upload("large.json", b"{" + b"x" * 30 + b"}"))
    assert not list(upload_root.glob("*"))


def test_migration_fields_constraints_and_legacy_nullable_compatibility(
    kb_session: Session, actors: dict[str, ActorContext]
) -> None:
    columns = {column["name"] for column in inspect(kb_session.bind).get_columns("documents")}
    assert {
        "rejection_reason",
        "mime_type",
        "file_size_bytes",
        "author_name",
        "organization",
        "publication_year",
    }.issubset(columns)
    legacy = Document(
        title="Legacy nullable metadata",
        file_name="legacy.pdf",
        file_type="PDF",
        storage_key="data/rag/raw/legacy.pdf",
        checksum_sha256=uuid4().hex + uuid4().hex,
        uploaded_by=actors["admin"].user_id,
    )
    kb_session.add(legacy)
    kb_session.commit()
    assert legacy.mime_type is legacy.file_size_bytes is legacy.publication_year is None

    for invalid_field in ({"file_size_bytes": 0}, {"publication_year": 1799}):
        invalid = Document(
            title="Invalid constraint",
            file_name="invalid.pdf",
            file_type="PDF",
            storage_key=f"data/rag/raw/{uuid4()}.pdf",
            checksum_sha256=uuid4().hex + uuid4().hex,
            uploaded_by=actors["admin"].user_id,
            **invalid_field,
        )
        with pytest.raises(IntegrityError):
            with kb_session.begin_nested():
                kb_session.add(invalid)
                kb_session.flush()

    duplicate_checksum = uuid4().hex + uuid4().hex
    first = Document(
        title="Checksum guard first",
        file_name="first.json",
        file_type="JSON",
        storage_key=f"data/rag/raw/{uuid4()}.json",
        checksum_sha256=duplicate_checksum,
        version_number=1,
        uploaded_by=actors["admin"].user_id,
    )
    kb_session.add(first)
    kb_session.commit()
    second = Document(
        title="Checksum guard second",
        file_name="second.json",
        file_type="JSON",
        storage_key=f"data/rag/raw/{uuid4()}.json",
        checksum_sha256=duplicate_checksum,
        version_number=2,
        uploaded_by=actors["admin"].user_id,
    )
    with pytest.raises(IntegrityError):
        with kb_session.begin_nested():
            kb_session.add(second)
            kb_session.flush()


@pytest.mark.anyio
async def test_http_upload_ownership_duplicate_rbac_and_safe_response(
    kb_session: Session,
    actors: dict[str, ActorContext],
    upload_root: Path,
) -> None:
    current = {"actor": actors["doctor"]}
    app = create_app()
    app.dependency_overrides[get_db] = lambda: kb_session
    app.dependency_overrides[get_current_actor] = lambda: current["actor"]
    payload = b'{"content":"Unique contribution bytes for HTTP test"}'
    form = {
        "title": "Doctor contribution",
        "source_name": "Synthetic public source",
        "author_name": "Nguyễn Văn A",
        "publication_year": "2026",
    }
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            created = await client.post(
                "/api/v1/documents/contributions",
                data=form,
                files={"file": ("knowledge.json", payload, "text/plain")},
            )
            assert created.status_code == 201, created.text
            body = created.json()
            assert body["approval_status"] == "PENDING"
            assert body["ingestion_status"] == "NOT_INGESTED"
            assert body["uploaded_by"] == str(actors["doctor"].user_id)
            assert "storage_key" not in body and "checksum_sha256" not in body
            document = kb_session.get(Document, body["id"])
            assert document is not None
            assert document.file_name == "knowledge.json"
            assert document.mime_type == "application/json"
            assert document.storage_key.startswith("data/rag/raw/uploads/")
            assert (BACKEND_ROOT / document.storage_key).is_file()

            own = await client.get("/api/v1/documents/contributions/me")
            assert own.status_code == 200
            assert body["id"] in {item["id"] for item in own.json()}

            current["actor"] = actors["other_doctor"]
            assert (
                await client.get(f"/api/v1/documents/contributions/{body['id']}")
            ).status_code == 403

            current["actor"] = actors["patient"]
            patient = await client.post(
                "/api/v1/documents/contributions",
                data=form,
                files={"file": ("patient.json", b'{"content":"patient"}', "application/json")},
            )
            assert patient.status_code == 403

            current["actor"] = actors["staff"]
            staff = await client.post(
                "/api/v1/documents/contributions",
                data=form,
                files={"file": ("staff.json", b'{"content":"staff"}', "application/json")},
            )
            assert staff.status_code == 403

            current["actor"] = actors["doctor"]
            duplicate = await client.post(
                "/api/v1/documents/contributions",
                data=form,
                files={"file": ("renamed.json", payload, "application/json")},
            )
            assert duplicate.status_code == 409
            assert duplicate.json()["error"]["code"] == "document_content_exists"
            assert "owner" not in duplicate.text.lower()

            spoof = await client.post(
                "/api/v1/documents/contributions",
                data={**form, "uploaded_by": str(actors["admin"].user_id), "approval_status": "APPROVED"},
                files={"file": ("spoof.json", b'{"content":"spoof unique"}', "application/json")},
            )
            assert spoof.status_code == 201
            assert spoof.json()["uploaded_by"] == str(actors["doctor"].user_id)
            assert spoof.json()["approval_status"] == "PENDING"
    finally:
        app.dependency_overrides.clear()
    assert len(list(upload_root.glob("*"))) == 2


@pytest.mark.anyio
async def test_resubmit_clears_review_and_transaction_failure_cleans_file(
    kb_session: Session,
    actors: dict[str, ActorContext],
    upload_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage = DocumentUploadStorage(get_settings())
    prepared = await storage.prepare(
        _upload("resubmit.json", b'{"content":"resubmit lifecycle"}')
    )
    service = DocumentService(kb_session)
    document = service.create_contribution(
        DocumentContributionCreate(title="Resubmit lifecycle"),
        prepared,
        actors["doctor"],
    )
    document.approval_status = ApprovalStatus.REJECTED
    document.rejection_reason = "Nguồn chưa rõ ràng"
    document.approved_by = actors["admin"].user_id
    kb_session.commit()
    updated = service.update_contribution(
        document.id,
        DocumentContributionUpdate(source_name="Nguồn đã bổ sung"),
        actors["doctor"],
    )
    assert updated.approval_status == ApprovalStatus.PENDING
    assert updated.ingestion_status == IngestionStatus.NOT_INGESTED
    assert updated.approved_by is updated.approved_at is updated.rejection_reason is None

    failed = await storage.prepare(
        _upload("rollback.json", b'{"content":"transaction cleanup bytes"}')
    )
    original_commit = kb_session.commit

    def fail_commit() -> None:
        raise RuntimeError("synthetic commit failure")

    monkeypatch.setattr(kb_session, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="synthetic commit failure"):
        service.create_contribution(
            DocumentContributionCreate(title="Rollback cleanup"),
            failed,
            actors["doctor"],
        )
    monkeypatch.setattr(kb_session, "commit", original_commit)
    assert not failed.temp_path.exists()
    assert not failed.final_path.exists()


def test_pending_contribution_is_not_rag_eligible(
    kb_session: Session, actors: dict[str, ActorContext]
) -> None:
    pending = Document(
        title="Pending is isolated",
        file_name="pending.json",
        file_type="JSON",
        storage_key="data/rag/raw/uploads/pending.json",
        checksum_sha256=uuid4().hex + uuid4().hex,
        uploaded_by=actors["doctor"].user_id,
        approval_status=ApprovalStatus.PENDING,
        ingestion_status=IngestionStatus.NOT_INGESTED,
    )
    kb_session.add(pending)
    kb_session.commit()
    eligible_ids = set(
        kb_session.scalars(
            select(Document.id).where(
                Document.approval_status == ApprovalStatus.APPROVED,
                Document.ingestion_status == IngestionStatus.COMPLETED,
            )
        )
    )
    assert pending.id not in eligible_ids


@pytest.mark.anyio
async def test_admin_file_review_and_review_lifecycle_are_safe(
    kb_session: Session,
    actors: dict[str, ActorContext],
    upload_root: Path,
) -> None:
    """KB-001C: original files are Admin-only and review keeps a strict lifecycle."""
    storage = DocumentUploadStorage(get_settings())
    payload = b'{"content":"KB-001C unique synthetic review document"}'
    prepared = await storage.prepare(_upload("kb001c-review.json", payload, "application/json"))
    document = DocumentService(kb_session).create_contribution(
        DocumentContributionCreate(title="KB-001C review document"),
        prepared,
        actors["doctor"],
    )
    original_storage_key = document.storage_key

    current = {"actor": actors["doctor"]}
    app = create_app()
    app.dependency_overrides[get_db] = lambda: kb_session
    app.dependency_overrides[get_current_actor] = lambda: current["actor"]
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            endpoint = f"/api/v1/documents/{document.id}/file"

            assert (await client.get(endpoint)).status_code == 403
            current["actor"] = actors["other_doctor"]
            assert (await client.get(endpoint)).status_code == 403
            current["actor"] = actors["staff"]
            assert (await client.get(endpoint)).status_code == 403
            current["actor"] = actors["patient"]
            assert (await client.get(endpoint)).status_code == 403

            current["actor"] = actors["admin"]
            downloaded = await client.get(endpoint)
            assert downloaded.status_code == 200
            assert downloaded.content == payload
            assert downloaded.headers["content-type"].startswith("application/json")
            assert "kb001c-review.json" in downloaded.headers["content-disposition"]
            assert str(BACKEND_ROOT) not in downloaded.text

            document.storage_key = "data/rag/raw/uploads/missing-kb001c.json"
            kb_session.commit()
            missing = await client.get(endpoint)
            assert missing.status_code == 404
            assert missing.json()["error"]["code"] == "document_file_not_found"
            assert str(BACKEND_ROOT) not in missing.text

            document.storage_key = "../outside-kb001c.json"
            kb_session.commit()
            escaped = await client.get(endpoint)
            assert escaped.status_code == 404
            assert str(BACKEND_ROOT) not in escaped.text

            document.storage_key = original_storage_key
            kb_session.commit()
            review_endpoint = f"/api/v1/documents/{document.id}/review"

            empty_reason = await client.post(
                review_endpoint,
                json={"approval_status": "REJECTED", "rejection_reason": "   "},
            )
            assert empty_reason.status_code == 422

            current["actor"] = actors["doctor"]
            assert (
                await client.post(review_endpoint, json={"approval_status": "APPROVED"})
            ).status_code == 403
            current["actor"] = actors["staff"]
            assert (
                await client.post(review_endpoint, json={"approval_status": "APPROVED"})
            ).status_code == 403

            current["actor"] = actors["admin"]
            rejected = await client.post(
                review_endpoint,
                json={"approval_status": "REJECTED", "rejection_reason": "Nguồn chưa đủ."},
            )
            assert rejected.status_code == 200
            assert rejected.json()["rejection_reason"] == "Nguồn chưa đủ."

            approved = await client.post(review_endpoint, json={"approval_status": "APPROVED"})
            assert approved.status_code == 200
            assert approved.json()["rejection_reason"] is None

            document.ingestion_status = IngestionStatus.COMPLETED
            kb_session.commit()
            wrong_lifecycle = await client.post(
                review_endpoint,
                json={"approval_status": "REJECTED", "rejection_reason": "Quá muộn."},
            )
            assert wrong_lifecycle.status_code == 409
            assert wrong_lifecycle.json()["error"]["code"] == "document_ingested"
    finally:
        app.dependency_overrides.clear()
