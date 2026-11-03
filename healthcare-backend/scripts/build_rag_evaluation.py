"""Build a deterministic anchor-to-article evaluation set from one corpus file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.documents.loaders import load_sources


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()
    if not 10 <= args.limit <= 1000:
        parser.error("--limit must be between 10 and 1000")
    queries: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for source in load_sources(args.source.resolve(), "JSON"):
        query = source.metadata.get("evaluation_query")
        article_id = source.external_id
        if not isinstance(query, str) or not query.strip() or not article_id:
            continue
        key = (query.strip(), article_id)
        if key in seen:
            continue
        seen.add(key)
        queries.append({"query": key[0], "expected_article_id": key[1]})
        if len(queries) >= args.limit:
            break
    if len(queries) < args.limit:
        raise RuntimeError(f"Only {len(queries)} grounded queries were available.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(queries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"EVALUATION_SET_OK queries={len(queries)} output={args.output.resolve()}")


if __name__ == "__main__":
    main()
