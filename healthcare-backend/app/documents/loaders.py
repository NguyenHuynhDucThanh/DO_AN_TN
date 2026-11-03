"""Streaming source loaders for the governed RAG corpus."""

from __future__ import annotations

import csv
import json
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import ijson
import pymupdf
from docx import Document as DocxDocument


class DocumentLoadError(ValueError):
    def __init__(self, message: str, code: str = "invalid_document") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class NormalizedSource:
    source_type: str
    source_name: str
    content: str
    external_id: str | None = None
    category: str | None = None
    title: str | None = None
    page_number: int | None = None
    section: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def normalize_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    lines = [" ".join(line.split()) for line in unicodedata.normalize("NFC", value).splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _dataset_record(record: object, source_name: str, row_number: int) -> NormalizedSource | None:
    if not isinstance(record, dict):
        raise DocumentLoadError(f"Record {row_number} must be a JSON object.", "invalid_json_record")
    content_field = next(
        (name for name in ("positive", "content", "text", "body", "answer") if name in record),
        None,
    )
    if content_field is None:
        raise DocumentLoadError(
            f"Record {row_number} has no supported factual content field.",
            "missing_content_field",
        )
    content = normalize_text(record.get(content_field))
    if not content:
        return None
    raw_meta = record.get("meta")
    meta = dict(raw_meta) if isinstance(raw_meta, dict) else {}
    article_id = meta.get("article_id")
    anchor = normalize_text(record.get("anchor"))
    metadata: dict[str, Any] = {
        "record_number": row_number,
        "content_field": content_field,
    }
    if anchor:
        metadata["evaluation_query"] = anchor
    # `negative` is intentionally neither copied to metadata nor emitted as factual content.
    for key, value in meta.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            metadata[key] = value
    return NormalizedSource(
        source_type="JSON",
        source_name=source_name,
        external_id=str(article_id) if article_id is not None else str(row_number),
        category=normalize_text(meta.get("category")) or None,
        title=normalize_text(meta.get("title")) or None,
        content=content,
        metadata=metadata,
    )


def detect_json_format(path: Path) -> tuple[str, str | None]:
    """Return jsonl, array, object-array, or object without loading the file."""
    with path.open("rb") as stream:
        first = b""
        while True:
            byte = stream.read(1)
            if not byte:
                raise DocumentLoadError("JSON file is empty.", "empty_document")
            if not byte.isspace():
                first = byte
                break
    if first == b"[":
        return "array", None
    if first != b"{":
        raise DocumentLoadError("JSON must begin with an object or array.", "invalid_json")

    with path.open("r", encoding="utf-8-sig") as stream:
        first_line = next((line for line in stream if line.strip()), "")
        try:
            first_object = json.loads(first_line)
        except json.JSONDecodeError:
            first_object = None
        if isinstance(first_object, dict) and any(
            key in first_object for key in ("positive", "content", "text", "body", "answer")
        ):
            return "jsonl", None

    try:
        with path.open("rb") as stream:
            root_key: str | None = None
            for prefix, event, value in ijson.parse(stream):
                if prefix == "" and event == "map_key":
                    root_key = str(value)
                elif root_key and prefix == root_key and event == "start_array":
                    return "object-array", root_key
                elif prefix == "" and event == "end_map":
                    break
    except ijson.JSONError as exc:
        raise DocumentLoadError("JSON is malformed.", "invalid_json") from exc
    return "object", None


def load_json(path: Path, *, limit: int | None = None) -> Iterator[NormalizedSource]:
    json_format, array_key = detect_json_format(path)
    source_name = path.name
    try:
        if json_format == "jsonl":
            with path.open("r", encoding="utf-8-sig") as stream:
                records = (json.loads(line) for line in stream if line.strip())
                yield from _mapped_records(records, source_name, limit)
            return
        if json_format in {"array", "object-array"}:
            prefix = "item" if json_format == "array" else f"{array_key}.item"
            with path.open("rb") as stream:
                yield from _mapped_records(ijson.items(stream, prefix), source_name, limit)
            return
        with path.open("rb") as stream:
            record = next(ijson.items(stream, ""))
        mapped = _dataset_record(record, source_name, 1)
        if mapped is not None:
            yield mapped
    except (json.JSONDecodeError, UnicodeDecodeError, ijson.JSONError) as exc:
        raise DocumentLoadError("JSON is malformed or is not UTF-8.", "invalid_json") from exc


def _mapped_records(
    records: Iterator[object], source_name: str, limit: int | None
) -> Iterator[NormalizedSource]:
    for row_number, record in enumerate(records, 1):
        if limit is not None and row_number > limit:
            break
        mapped = _dataset_record(record, source_name, row_number)
        if mapped is not None:
            yield mapped


def load_csv(path: Path, *, limit: int | None = None) -> Iterator[NormalizedSource]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames:
                raise DocumentLoadError("CSV has no header.", "invalid_csv")
            content_field = next(
                (name for name in ("positive", "content", "text", "body", "answer") if name in reader.fieldnames),
                None,
            )
            if content_field is None:
                raise DocumentLoadError("CSV has no supported content column.", "missing_content_field")
            for row_number, row in enumerate(reader, 1):
                if limit is not None and row_number > limit:
                    break
                content = normalize_text(row.get(content_field))
                if not content:
                    continue
                metadata = {
                    key: normalize_text(value)
                    for key, value in row.items()
                    if key not in {content_field, "negative"} and normalize_text(value)
                }
                yield NormalizedSource(
                    source_type="CSV",
                    source_name=path.name,
                    external_id=metadata.get("article_id") or str(row_number),
                    category=metadata.get("category"),
                    title=metadata.get("title"),
                    content=content,
                    metadata={"row_number": row_number, **metadata},
                )
    except (csv.Error, UnicodeDecodeError) as exc:
        raise DocumentLoadError("CSV is malformed or is not UTF-8.", "invalid_csv") from exc


def load_pdf(path: Path, *, limit: int | None = None) -> Iterator[NormalizedSource]:
    try:
        pdf = pymupdf.open(path)
    except Exception as exc:
        raise DocumentLoadError("PDF is invalid.", "invalid_pdf") from exc
    extracted = 0
    try:
        for page_index, page in enumerate(pdf):
            if limit is not None and extracted >= limit:
                break
            content = normalize_text(page.get_text("text"))
            if not content:
                continue
            extracted += 1
            yield NormalizedSource(
                source_type="PDF",
                source_name=path.name,
                external_id=f"page-{page_index + 1}",
                page_number=page_index + 1,
                content=content,
                metadata={"page": page_index + 1},
            )
    finally:
        pdf.close()
    if extracted == 0:
        raise DocumentLoadError(
            "PDF has no extractable text; OCR is outside RAG V1.",
            "no_extractable_text",
        )


def load_docx(path: Path, *, limit: int | None = None) -> Iterator[NormalizedSource]:
    try:
        document = DocxDocument(path)
    except Exception as exc:
        raise DocumentLoadError("DOCX is invalid.", "invalid_docx") from exc
    current_heading: str | None = None
    paragraphs: list[str] = []
    section_index = 0

    def emit() -> NormalizedSource | None:
        nonlocal section_index, paragraphs
        content = normalize_text("\n".join(paragraphs))
        paragraphs = []
        if not content:
            return None
        section_index += 1
        return NormalizedSource(
            source_type="DOCX",
            source_name=path.name,
            external_id=f"section-{section_index}",
            section=current_heading,
            title=current_heading,
            content=content,
            metadata={"section_index": section_index},
        )

    for paragraph in document.paragraphs:
        text = normalize_text(paragraph.text)
        if not text:
            continue
        if paragraph.style and paragraph.style.name.lower().startswith("heading"):
            source = emit()
            if source is not None:
                yield source
                if limit is not None and section_index >= limit:
                    return
            current_heading = text
        else:
            paragraphs.append(text)
    source = emit()
    if source is not None and (limit is None or section_index <= limit):
        yield source


def load_sources(path: Path, file_type: str, *, limit: int | None = None) -> Iterator[NormalizedSource]:
    loaders = {
        "JSON": load_json,
        "CSV": load_csv,
        "PDF": load_pdf,
        "DOCX": load_docx,
    }
    try:
        loader = loaders[file_type.upper()]
    except KeyError as exc:
        raise DocumentLoadError("Unsupported document type.", "unsupported_document_type") from exc
    yield from loader(path, limit=limit)
