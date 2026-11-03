"""Benchmark all Phase 12 strategies on one frozen query set and corpus."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import gc
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import BACKEND_ROOT, get_settings
from app.core.database import get_session_factory
from app.documents.embeddings import EmbeddingService
from app.rag.evaluation import EvaluationQuery, evaluate_vectors
from app.rag.factory import build_retriever
from app.rag.retrieval import ExactDenseRetriever, HnswDenseRetriever

STRATEGIES = ("exact_dense", "hnsw_dense", "hybrid_rrf", "hybrid_rerank")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evaluation-file",
        type=Path,
        default=BACKEND_ROOT / "app" / "rag" / "evaluation_phase12.json",
    )
    parser.add_argument("--strategies", nargs="+", choices=STRATEGIES, default=list(STRATEGIES))
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args()

    settings = get_settings()
    queries = [
        EvaluationQuery(**item)
        for item in json.loads(args.evaluation_file.read_text(encoding="utf-8"))
    ]
    embeddings = EmbeddingService(settings.embedding_model, settings.embedding_batch_size)
    vectors = embeddings.embed([item.query for item in queries])
    embeddings.release_model()
    gc.collect()
    results: list[dict] = []
    with get_session_factory()() as session:
        for name in args.strategies:
            retriever = build_retriever(session, settings, strategy=name, experiment_mode=True)
            result = evaluate_vectors(queries, vectors, retriever)
            row = {"strategy": name, "top_k": settings.rag_top_k, **asdict(result)}
            if isinstance(retriever, HnswDenseRetriever):
                row["hnsw_plan"] = ExactDenseRetriever.uses_hnsw(
                    retriever.explain_hnsw(vectors[0])
                )
            if isinstance(retriever, ExactDenseRetriever) and not isinstance(retriever, HnswDenseRetriever):
                row["exact_plan"] = not retriever.uses_hnsw(retriever.explain_exact(vectors[0]))
            results.append(row)
            session.rollback()

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fieldnames = sorted({key for row in results for key in row})
    with args.output_csv.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
