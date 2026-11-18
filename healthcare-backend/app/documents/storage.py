"""Small, Windows-safe runtime storage helper for governed document uploads."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
import tempfile
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

from fastapi import UploadFile

from app.core.config import BACKEND_ROOT, Settings
from app.core.errors import BadRequestError, ConflictError, NotFoundError, PayloadTooLargeError
from app.documents.loaders import DocumentLoadError, load_sources


FORMAT_BY_EXTENSION = {
    ".pdf": ("PDF", "application/pdf"),
    ".docx": (
        "DOCX",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
    ".csv": ("CSV", "text/csv"),
    ".json": ("JSON", "application/json"),
    ".jsonl": ("JSON", "application/x-ndjson"),
}


@dataclass(slots=True)
class PreparedDocumentUpload:
    original_filename: str
    file_type: str
    mime_type: str
    file_size_bytes: int
    checksum_sha256: str
    storage_key: str
    temp_path: Path
    final_path: Path
    finalized: bool = False

    def finalize(self) -> None:
        """Create the final name atomically without ever overwriting another file."""
        try:
            os.link(self.temp_path, self.final_path)
        except FileExistsError as exc:
            raise ConflictError(
                "A storage filename collision occurred. Please retry.",
                "document_storage_collision",
            ) from exc
        self.temp_path.unlink(missing_ok=True)
        self.finalized = True

    def cleanup(self) -> None:
        self.temp_path.unlink(missing_ok=True)
        if self.finalized:
            self.final_path.unlink(missing_ok=True)
            self.finalized = False


class DocumentUploadStorage:
    def __init__(self, settings: Settings) -> None:
        self.max_bytes = settings.document_upload_max_bytes
        self.root = (BACKEND_ROOT / settings.document_upload_root).resolve()
        allowed_root = (BACKEND_ROOT / "data" / "rag" / "raw").resolve()
        if not self.root.is_relative_to(allowed_root):
            raise ValueError("Document upload root is outside data/rag/raw")
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def resolve_existing(storage_key: str) -> Path:
        raw_root = (BACKEND_ROOT / "data" / "rag" / "raw").resolve()
        key = Path(storage_key)
        if key.is_absolute():
            raise NotFoundError("Document file was not found.", "document_file_not_found")
        path = (BACKEND_ROOT / key).resolve()
        if not path.is_relative_to(raw_root) or not path.is_file():
            raise NotFoundError("Document file was not found.", "document_file_not_found")
        return path

    async def prepare(self, upload: UploadFile) -> PreparedDocumentUpload:
        original_filename, suffix, file_type, mime_type = self._identify(upload.filename)
        temp_path: Path | None = None
        size = 0
        digest = hashlib.sha256()
        try:
            with tempfile.NamedTemporaryFile(
                mode="xb",
                prefix=".upload-",
                suffix=suffix,
                dir=self.root,
                delete=False,
            ) as temporary:
                temp_path = Path(temporary.name)
                while block := await upload.read(1024 * 1024):
                    size += len(block)
                    if size > self.max_bytes:
                        raise PayloadTooLargeError()
                    digest.update(block)
                    temporary.write(block)
            if size == 0:
                raise BadRequestError("Document file is empty.", "empty_document")
            self._validate_content(temp_path, suffix, file_type)
            generated_name = f"{uuid4()}{suffix}"
            final_path = (self.root / generated_name).resolve()
            if final_path.parent != self.root or not final_path.is_relative_to(self.root):
                raise BadRequestError("Invalid document storage path.", "invalid_document_path")
            storage_key = final_path.relative_to(BACKEND_ROOT).as_posix()
            return PreparedDocumentUpload(
                original_filename=original_filename,
                file_type=file_type,
                mime_type=mime_type,
                file_size_bytes=size,
                checksum_sha256=digest.hexdigest(),
                storage_key=storage_key,
                temp_path=temp_path,
                final_path=final_path,
            )
        except Exception:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            raise

    @staticmethod
    def _identify(filename: str | None) -> tuple[str, str, str, str]:
        raw_name = (filename or "").strip()
        if (
            not raw_name
            or len(raw_name) > 255
            or "/" in raw_name
            or "\\" in raw_name
            or raw_name in {".", ".."}
        ):
            raise BadRequestError("Document filename is invalid.", "invalid_document_filename")
        suffix = Path(raw_name).suffix.lower()
        try:
            file_type, mime_type = FORMAT_BY_EXTENSION[suffix]
        except KeyError as exc:
            raise BadRequestError(
                "Document format is not supported.", "unsupported_document_format"
            ) from exc
        return raw_name, suffix, file_type, mime_type

    @staticmethod
    def _validate_content(path: Path, suffix: str, file_type: str) -> None:
        try:
            if suffix == ".pdf":
                with path.open("rb") as stream:
                    if stream.read(5) != b"%PDF-":
                        raise BadRequestError(
                            "PDF content is invalid.", "invalid_document_content"
                        )
            if suffix == ".docx":
                try:
                    with ZipFile(path) as archive:
                        members = set(archive.namelist())
                except (BadZipFile, OSError) as exc:
                    raise BadRequestError(
                        "DOCX content is invalid.", "invalid_document_content"
                    ) from exc
                if not {"[Content_Types].xml", "word/document.xml"}.issubset(members):
                    raise BadRequestError("DOCX content is invalid.", "invalid_document_content")
            usable_records = sum(1 for _source in load_sources(path, file_type))
            if usable_records == 0:
                raise BadRequestError(
                    "Document contains no usable content.", "empty_document"
                )
        except DocumentLoadError as exc:
            raise BadRequestError(str(exc), exc.code) from exc
