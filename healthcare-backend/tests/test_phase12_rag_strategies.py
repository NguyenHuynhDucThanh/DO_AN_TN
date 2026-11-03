"""Phase 12 BM25, RRF, reranking and fallback tests with small fixtures."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import UUID

import pytest

from app.rag.retrieval import (
    BgeReranker,
    Bm25Retriever,
    FallbackRetriever,
    HybridRerankRetriever,
    HybridRrfRetriever,
    reciprocal_rank_fusion,
)
from app.rag.schemas import RagSource, RetrievedChunk


def chunk(number: int, content: str, article_id: str) -> RetrievedChunk:
    return RetrievedChunk(
        content=content,
        distance=0.1 * number,
        source=RagSource(
            document_id=UUID("00000000-0000-0000-0000-000000000001"),
            title=f"Nguồn {article_id}",
            category="demo",
            source_name="fixture",
            article_id=article_id,
            page=number,
        ),
        chunk_id=UUID(f"00000000-0000-0000-0000-{number:012d}"),
    )


def test_vietnamese_bm25_unicode_ranking_and_empty_query() -> None:
    corpus = [
        chunk(1, "Người bệnh đau họng và sổ mũi.", "a"),
        chunk(2, "Thông tin khám tim mạch và lịch hẹn.", "b"),
        chunk(3, "Đau đầu có nhiều nguyên nhân.", "c"),
    ]
    retriever = Bm25Retriever(None, top_k=3, corpus=corpus)
    assert retriever.tokenize("ĐAU HỌNG") == ["đau", "họng"]
    results = retriever.retrieve([], query_text="Tôi bị đau họng")
    assert results[0].source.article_id == "a"
    assert results[0].source.title == "Nguồn a"
    assert retriever.retrieve([], query_text="  ") == []


def test_rrf_dense_sparse_overlap_and_deterministic_order() -> None:
    first = chunk(1, "dense only", "a")
    overlap = chunk(2, "both", "b")
    third = chunk(3, "sparse only", "c")
    expected = reciprocal_rank_fusion(
        [[first, overlap], [overlap, third]], rrf_k=60, top_k=3
    )
    repeated = reciprocal_rank_fusion(
        [[first, overlap], [overlap, third]], rrf_k=60, top_k=3
    )
    assert expected[0].source.article_id == "b"
    assert {item.source.article_id for item in expected} == {"a", "b", "c"}
    assert [item.chunk_id for item in expected] == [item.chunk_id for item in repeated]


def test_hybrid_rrf_sparse_failure_falls_back_to_dense() -> None:
    dense = MagicMock()
    dense.retrieve.return_value = [chunk(1, "dense", "a")]
    sparse = MagicMock()
    sparse.retrieve.side_effect = RuntimeError("sparse unavailable")
    hybrid = HybridRrfRetriever(dense, sparse, rrf_k=60, top_k=5)
    assert hybrid.retrieve([0.0], query_text="query")[0].source.article_id == "a"


class FakeRerankerModel:
    def predict(self, pairs, **kwargs):
        assert kwargs["batch_size"] == 2
        return [0.1, 0.9]


def test_reranker_candidate_order_top_k_empty_and_source_traceability() -> None:
    candidates = [chunk(1, "ít phù hợp", "a"), chunk(2, "rất phù hợp", "b")]
    reranker = BgeReranker(
        "synthetic", batch_size=2, model_factory=lambda *_args, **_kwargs: FakeRerankerModel()
    )
    results = reranker.rerank("câu hỏi", candidates, top_k=1)
    assert results[0].source.article_id == "b"
    assert results[0].source.source_name == "fixture"
    assert reranker.rerank("query", [], top_k=5) == []


def test_reranker_and_strategy_failure_preserve_previous_result() -> None:
    candidate = chunk(1, "candidate", "a")
    hybrid = MagicMock()
    hybrid.retrieve.return_value = [candidate]
    reranker = MagicMock()
    reranker.rerank.side_effect = RuntimeError("model unavailable")
    strategy = HybridRerankRetriever(hybrid, reranker, top_k=5)
    assert strategy.retrieve([0.0], query_text="query") == [candidate]

    primary = MagicMock()
    primary.retrieve.side_effect = RuntimeError("advanced failure")
    fallback = MagicMock()
    fallback.retrieve.return_value = [candidate]
    assert FallbackRetriever(primary, fallback).retrieve([0.0], query_text="query") == [candidate]


def test_rrf_rejects_invalid_parameters() -> None:
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([], rrf_k=0, top_k=5)
