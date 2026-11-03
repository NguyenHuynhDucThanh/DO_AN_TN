"""Run versioned Recall@K, Hit@K and MRR against exact pgvector retrieval."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import BACKEND_ROOT, get_settings
from app.core.database import get_session_factory
from app.documents.embeddings import EmbeddingService
from app.rag.evaluation import EvaluationQuery, evaluate
from app.rag.retrieval import ExactDenseRetriever


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evaluation-file",
        type=Path,
        default=BACKEND_ROOT / "app" / "rag" / "evaluation_v1.json",
    )
    args = parser.parse_args()
    settings = get_settings()
    path = args.evaluation_file.resolve()
    queries = [EvaluationQuery(**item) for item in json.loads(path.read_text(encoding="utf-8"))]
    embeddings = EmbeddingService(settings.embedding_model, settings.embedding_batch_size)
    with get_session_factory()() as session:
        retriever = ExactDenseRetriever(
            session, top_k=settings.rag_top_k, max_distance=settings.rag_max_cosine_distance
        )
        result = evaluate(queries, embeddings, retriever)
        plan = retriever.explain_exact(embeddings.embed([queries[0].query])[0])
        if retriever.uses_hnsw(plan):
            raise RuntimeError("Exact baseline unexpectedly used HNSW")
    print(
        f"queries={result.query_count} top_k={settings.rag_top_k} "
        f"recall_at_k={result.recall_at_k:.4f} hit_at_k={result.hit_at_k:.4f} mrr={result.mrr:.4f} exact_plan=true"
    )


if __name__ == "__main__":
    main()
