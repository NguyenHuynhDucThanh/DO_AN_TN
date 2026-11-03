"""Repeatable retrieval metrics shared by all Phase 12 strategies."""

from dataclasses import dataclass
import statistics
import time

from app.documents.embeddings import EmbeddingService
from app.rag.retrieval import RetrievalStrategy


@dataclass(frozen=True)
class EvaluationQuery:
    query: str
    expected_article_id: str


@dataclass(frozen=True)
class EvaluationResult:
    query_count: int
    hit_at_k: float
    recall_at_k: float
    mrr: float
    latency_mean_ms: float
    latency_median_ms: float
    latency_p95_ms: float
    reranking_mean_ms: float = 0.0


def evaluate(
    queries: list[EvaluationQuery],
    embeddings: EmbeddingService,
    retriever: RetrievalStrategy,
) -> EvaluationResult:
    vectors = embeddings.embed([item.query for item in queries])
    return evaluate_vectors(queries, vectors, retriever)


def evaluate_vectors(
    queries: list[EvaluationQuery],
    vectors: list[list[float]],
    retriever: RetrievalStrategy,
) -> EvaluationResult:
    if not queries:
        raise ValueError("Evaluation set must not be empty.")
    if len(queries) != len(vectors):
        raise ValueError("Evaluation queries and vectors must have equal length.")
    hits = 0
    reciprocal_rank = 0.0
    latencies: list[float] = []
    reranking_latencies: list[float] = []
    for item, vector in zip(queries, vectors, strict=True):
        started = time.perf_counter()
        results = retriever.retrieve(vector, query_text=item.query)
        latencies.append((time.perf_counter() - started) * 1000)
        reranking_latencies.append(
            float(getattr(retriever, "last_rerank_seconds", 0.0)) * 1000
        )
        rank = next(
            (
                index
                for index, result in enumerate(results, 1)
                if result.source.article_id == item.expected_article_id
            ),
            None,
        )
        if rank is not None:
            hits += 1
            reciprocal_rank += 1 / rank
    score = hits / len(queries)
    ordered = sorted(latencies)
    p95_index = max(0, _ceil(0.95 * len(ordered)) - 1)
    return EvaluationResult(
        query_count=len(queries),
        hit_at_k=score,
        recall_at_k=score,
        mrr=reciprocal_rank / len(queries),
        latency_mean_ms=statistics.fmean(latencies),
        latency_median_ms=statistics.median(latencies),
        latency_p95_ms=ordered[p95_index],
        reranking_mean_ms=statistics.fmean(reranking_latencies),
    )


def _ceil(value: float) -> int:
    integer = int(value)
    return integer if integer == value else integer + 1
