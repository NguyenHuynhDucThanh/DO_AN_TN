"""Explicit smoke/full ingestion command; Backend startup never calls this script."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth.context import ActorContext
from app.core.config import get_settings
from app.core.database import get_session_factory
from app.documents.chunking import chunk_source, content_hash
from app.documents.ingestion import DocumentIngestionService
from app.documents.loaders import load_sources
from app.users.repository import UserRepository


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--document-id", type=UUID, required=True)
    actor_group = parser.add_mutually_exclusive_group(required=True)
    actor_group.add_argument("--actor-user-id", type=UUID)
    actor_group.add_argument("--actor-email")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    if args.batch_size is not None:
        settings.embedding_batch_size = args.batch_size

    with get_session_factory()() as session:
        repository = UserRepository(session)
        user = (
            repository.get(args.actor_user_id)
            if args.actor_user_id is not None
            else repository.get_by_email(args.actor_email)
        )
        roles = repository.active_role_codes(user.id) if user is not None else frozenset()
        if user is None or "ADMIN" not in roles:
            parser.error("actor must be an existing active ADMIN")
        actor = ActorContext(user_id=user.id, roles=roles)
        service = DocumentIngestionService(session, settings)
        if args.dry_run:
            document = service.repository.get(args.document_id)
            if document is None:
                parser.error("document does not exist")
            path = service._resolve_source(document.storage_key, args.source)
            seen: set[str] = set()
            raw = unique = chunks = 0
            for source in load_sources(path, document.file_type, limit=args.limit):
                raw += 1
                digest = content_hash(source.content)
                if digest in seen:
                    continue
                seen.add(digest)
                unique += 1
                chunks += len(chunk_source(source, max_chars=settings.rag_chunk_max_chars, overlap_chars=settings.rag_chunk_overlap_chars))
            print(f"DRY_RUN raw_records={raw} unique_contents={unique} duplicates_removed={raw-unique} chunks={chunks}")
            return
        summary = service.ingest(
            args.document_id,
            actor,
            source_override=args.source,
            limit=args.limit,
            progress_callback=lambda records, chunks: print(
                f"progress raw_records={records} embedded_chunks={chunks}", flush=True
            ),
        )
        controlled_subset = args.limit is not None or (
            args.source
            and ("subset" in args.source.name or ".large-" in args.source.name)
        )
        mode = "LARGE_CONTROLLED_SUBSET" if controlled_subset else "FULL"
        print(f"{mode}_INGESTION_PASS {summary.model_dump_json()}")


if __name__ == "__main__":
    main()
