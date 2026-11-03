"""Inspect a RAG file without embedding or loading the full file into memory."""

from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.documents.loaders import detect_json_format, load_sources


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--file-type", choices=["JSON", "CSV", "PDF", "DOCX"], required=True)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    path = args.source.resolve()
    if not path.is_file():
        parser.error("source file does not exist")
    if args.file_type == "JSON":
        detected, array_key = detect_json_format(path)
        print(f"json_format={detected} array_key={array_key or '-'}")
    raw = 0
    hashes: set[str] = set()
    article_ids: set[str] = set()
    for source in load_sources(path, args.file_type, limit=args.limit):
        raw += 1
        hashes.add(sha256(source.content.encode("utf-8")).hexdigest())
        if source.external_id:
            article_ids.add(source.external_id)
    print(f"source_bytes={path.stat().st_size}")
    print(f"raw_records={raw}")
    print(f"unique_articles={len(article_ids)}")
    print(f"unique_contents={len(hashes)}")
    print(f"duplicates_removed={raw - len(hashes)}")


if __name__ == "__main__":
    main()
