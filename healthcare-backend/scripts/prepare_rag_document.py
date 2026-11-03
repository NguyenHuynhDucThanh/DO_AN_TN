"""Register and approve a local RAG source through the existing Document workflow."""

from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
import sys
from uuid import UUID

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth.context import ActorContext
from app.core.config import BACKEND_ROOT
from app.core.database import get_session_factory
from app.documents.schemas import DocumentCreate, DocumentReview
from app.documents.service import DocumentService
from app.models.enums import ApprovalStatus, UserStatus
from app.models.knowledge import Document
from app.users.repository import UserRepository


def _checksum(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _type_for(path: Path) -> str:
    mapping = {".json": "JSON", ".jsonl": "JSON", ".csv": "CSV", ".pdf": "PDF", ".docx": "DOCX"}
    try:
        return mapping[path.suffix.lower()]
    except KeyError as exc:
        raise ValueError("Source extension must be JSON, JSONL, CSV, PDF, or DOCX.") from exc


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    actor_group = parser.add_mutually_exclusive_group(required=True)
    actor_group.add_argument("--actor-user-id", type=UUID)
    actor_group.add_argument("--actor-email")
    parser.add_argument("--title", default="Vietnamese Medical Dataset")
    parser.add_argument("--source-name", default="mtue29/vietnamese-medical-dataset")
    parser.add_argument("--source-url", default="https://huggingface.co/datasets/mtue29/vietnamese-medical-dataset")
    parser.add_argument("--version", type=int, default=1)
    args = parser.parse_args()

    path = args.source.resolve()
    raw_root = (BACKEND_ROOT / "data" / "rag" / "raw").resolve()
    if not path.is_file() or not path.is_relative_to(raw_root):
        parser.error(f"source must be an existing file below {raw_root}")
    checksum = _checksum(path)

    with get_session_factory()() as session:
        users = UserRepository(session)
        actor_user = (
            users.get(args.actor_user_id)
            if args.actor_user_id is not None
            else users.get_by_email(args.actor_email)
        )
        roles = users.active_role_codes(actor_user.id) if actor_user is not None else frozenset()
        if actor_user is None or actor_user.status != UserStatus.ACTIVE or "ADMIN" not in roles:
            parser.error("actor must be an existing active ADMIN")
        actor = ActorContext(user_id=actor_user.id, roles=roles)

        existing = session.scalar(
            select(Document).where(
                Document.checksum_sha256 == checksum,
                Document.version_number == args.version,
            )
        )
        service = DocumentService(session)
        if existing is None:
            relative_key = path.relative_to(BACKEND_ROOT).as_posix()
            existing = service.create(
                DocumentCreate(
                    title=args.title,
                    file_name=path.name,
                    file_type=_type_for(path),
                    storage_key=relative_key,
                    source_name=args.source_name,
                    source_url=args.source_url,
                    checksum_sha256=checksum,
                    version_number=args.version,
                ),
                actor,
            )
        if existing.approval_status == ApprovalStatus.PENDING:
            existing = service.review(
                existing.id,
                DocumentReview(approval_status=ApprovalStatus.APPROVED),
                actor,
            )
        if existing.approval_status != ApprovalStatus.APPROVED:
            parser.error("matching Document exists but is not APPROVED")
        print(
            f"DOCUMENT_READY document_id={existing.id} actor_user_id={actor.user_id} "
            f"approval={existing.approval_status.value} ingestion={existing.ingestion_status.value}"
        )


if __name__ == "__main__":
    main()
