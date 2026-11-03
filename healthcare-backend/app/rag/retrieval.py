"""Configurable dense, sparse, fusion and reranking strategies over one corpus."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
import gc
import math
import re
import time
import unicodedata
from typing import Any, Protocol

from sqlalchemy import select, text
from sqlalchemy.orm import Session, aliased

from app.core.model_runtime import HEAVY_MODEL_LOCK
from app.documents.embeddings import get_embedding_service
from app.models.enums import ApprovalStatus, IngestionStatus
from app.models.knowledge import Document, DocumentChunk, EMBEDDING_DIMENSION
from app.rag.schemas import RagSource, RetrievedChunk


class RetrievalStrategy(Protocol):
    def retrieve(
        self, query_vector: list[float], *, query_text: str | None = None
    ) -> list[RetrievedChunk]: ...


class ExactDenseRetriever:
    strategy_name = "exact_dense"

    def __init__(self, session: Session, *, top_k: int, max_distance: float) -> None:
        self.session = session
        self.top_k = top_k
        self.max_distance = max_distance

    @staticmethod
    def _validate_vector(vector: list[float]) -> None:
        if len(vector) != EMBEDDING_DIMENSION:
            raise ValueError(f"Query embedding must have {EMBEDDING_DIMENSION} dimensions.")

    def _statement(self, query_vector: list[float]):
        distance = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")
        return (
            select(DocumentChunk, Document, distance)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                Document.approval_status == ApprovalStatus.APPROVED,
                Document.ingestion_status == IngestionStatus.COMPLETED,
            )
            .order_by(distance)
            .limit(self.top_k)
        )

    def retrieve(
        self, query_vector: list[float], *, query_text: str | None = None
    ) -> list[RetrievedChunk]:
        del query_text
        self._validate_vector(query_vector)
        self.session.execute(text("SET LOCAL enable_indexscan = off"))
        return self._execute(self._statement(query_vector))

    def _execute(self, statement) -> list[RetrievedChunk]:
        results: list[RetrievedChunk] = []
        for chunk, document, value in self.session.execute(statement):
            numeric_distance = float(value)
            if numeric_distance > self.max_distance:
                continue
            results.append(_retrieved_chunk(chunk, document, numeric_distance))
        return results

    def explain_exact(self, query_vector: list[float]) -> dict[str, Any]:
        self._validate_vector(query_vector)
        self.session.execute(text("SET LOCAL enable_indexscan = off"))
        return _explain(self.session, query_vector, self.top_k)

    @staticmethod
    def uses_hnsw(plan: dict[str, Any]) -> bool:
        return "ix_document_chunks_embedding_hnsw" in str(plan)


class HnswDenseRetriever(ExactDenseRetriever):
    strategy_name = "hnsw_dense"

    def __init__(
        self,
        session: Session,
        *,
        top_k: int,
        max_distance: float,
        ef_search: int,
    ) -> None:
        super().__init__(session, top_k=top_k, max_distance=max_distance)
        if not 1 <= ef_search <= 1000:
            raise ValueError("HNSW ef_search must be between 1 and 1000.")
        self.ef_search = ef_search

    def _enable_hnsw(self) -> None:
        self.session.execute(text("SET LOCAL enable_indexscan = on"))
        self.session.execute(text("SET LOCAL enable_seqscan = off"))
        self.session.execute(text(f"SET LOCAL hnsw.ef_search = {self.ef_search}"))

    def _statement(self, query_vector: list[float]):
        distance = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")
        candidate_limit = max(self.top_k * 5, self.top_k)
        candidates = (
            select(DocumentChunk, distance)
            .order_by(distance)
            .limit(candidate_limit)
            .subquery("hnsw_candidates")
        )
        candidate_chunk = aliased(DocumentChunk, candidates)
        return (
            select(candidate_chunk, Document, candidates.c.distance)
            .join(Document, Document.id == candidate_chunk.document_id)
            .where(
                Document.approval_status == ApprovalStatus.APPROVED,
                Document.ingestion_status == IngestionStatus.COMPLETED,
            )
            .order_by(candidates.c.distance)
            .limit(self.top_k)
        )

    def retrieve(
        self, query_vector: list[float], *, query_text: str | None = None
    ) -> list[RetrievedChunk]:
        del query_text
        self._validate_vector(query_vector)
        self._enable_hnsw()
        return self._execute(self._statement(query_vector))

    def explain_hnsw(self, query_vector: list[float]) -> dict[str, Any]:
        self._validate_vector(query_vector)
        self._enable_hnsw()
        vector_literal = "[" + ",".join(str(float(value)) for value in query_vector) + "]"
        plan = self.session.execute(
            text(
                """
                EXPLAIN (FORMAT JSON)
                WITH candidates AS MATERIALIZED (
                    SELECT dc.id, dc.document_id,
                           dc.embedding <=> CAST(:query_vector AS vector) AS distance
                    FROM document_chunks AS dc
                    ORDER BY dc.embedding <=> CAST(:query_vector AS vector)
                    LIMIT :candidate_limit
                )
                SELECT candidates.id
                FROM candidates
                JOIN documents AS d ON d.id = candidates.document_id
                WHERE d.approval_status = 'APPROVED'
                  AND d.ingestion_status = 'COMPLETED'
                ORDER BY candidates.distance
                LIMIT :top_k
                """
            ),
            {
                "query_vector": vector_literal,
                "candidate_limit": max(self.top_k * 5, self.top_k),
                "top_k": self.top_k,
            },
        ).scalar_one()
        return plan[0] if isinstance(plan, list) else plan


class Bm25Retriever:
    """BM25 with Unicode NFC/casefold tokenization that preserves Vietnamese accents."""

    strategy_name = "bm25"

    def __init__(
        self,
        session: Session | None,
        *,
        top_k: int,
        k1: float = 1.5,
        b: float = 0.75,
        corpus: Sequence[RetrievedChunk] | None = None,
    ) -> None:
        if top_k < 1:
            raise ValueError("BM25 top_k must be positive.")
        if not 0 < k1 <= 3 or not 0 <= b <= 1:
            raise ValueError("Invalid BM25 parameters.")
        self.session = session
        self.top_k = top_k
        self.k1 = k1
        self.b = b
        self._provided_corpus = list(corpus) if corpus is not None else None

    @staticmethod
    def tokenize(value: str) -> list[str]:
        normalized = unicodedata.normalize("NFC", value).casefold()
        return re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)

    def _corpus(self) -> list[RetrievedChunk]:
        if self._provided_corpus is not None:
            return self._provided_corpus
        if self.session is None:
            return []
        statement = (
            select(DocumentChunk, Document)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                Document.approval_status == ApprovalStatus.APPROVED,
                Document.ingestion_status == IngestionStatus.COMPLETED,
            )
            .order_by(DocumentChunk.id)
        )
        return [
            _retrieved_chunk(chunk, document, 1.0)
            for chunk, document in self.session.execute(statement)
        ]

    def retrieve(
        self, query_vector: list[float], *, query_text: str | None = None
    ) -> list[RetrievedChunk]:
        del query_vector
        query_tokens = self.tokenize(query_text or "")
        if not query_tokens:
            return []
        corpus = self._corpus()
        if not corpus:
            return []
        documents = [self.tokenize(item.content) for item in corpus]
        lengths = [len(tokens) for tokens in documents]
        average_length = sum(lengths) / len(lengths) if lengths else 0.0
        frequencies = [Counter(tokens) for tokens in documents]
        document_frequency = Counter(
            token for frequency in frequencies for token in frequency.keys()
        )
        scored: list[tuple[float, str, RetrievedChunk]] = []
        for item, frequency, length in zip(corpus, frequencies, lengths, strict=True):
            score = 0.0
            for token in query_tokens:
                term_frequency = frequency.get(token, 0)
                if term_frequency == 0:
                    continue
                df = document_frequency[token]
                inverse_document_frequency = math.log(
                    1 + (len(corpus) - df + 0.5) / (df + 0.5)
                )
                normalization = self.k1 * (
                    1 - self.b + self.b * length / max(average_length, 1.0)
                )
                score += inverse_document_frequency * (
                    term_frequency * (self.k1 + 1) / (term_frequency + normalization)
                )
            if score > 0:
                scored.append((score, _chunk_key(item), item))
        scored.sort(key=lambda value: (-value[0], value[1]))
        return [
            RetrievedChunk(
                content=item.content,
                distance=1.0 / (1.0 + score),
                source=item.source,
                chunk_id=item.chunk_id,
            )
            for score, _key, item in scored[: self.top_k]
        ]


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[RetrievedChunk]], *, rrf_k: int, top_k: int
) -> list[RetrievedChunk]:
    if rrf_k < 1 or top_k < 1:
        raise ValueError("RRF parameters must be positive.")
    scores: dict[str, float] = {}
    chunks: dict[str, RetrievedChunk] = {}
    for ranking in rankings:
        for rank, chunk in enumerate(ranking, 1):
            key = _chunk_key(chunk)
            scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank)
            chunks.setdefault(key, chunk)
    ordered = sorted(scores, key=lambda key: (-scores[key], key))
    return [
        RetrievedChunk(
            content=chunks[key].content,
            distance=1.0 / (1.0 + scores[key]),
            source=chunks[key].source,
            chunk_id=chunks[key].chunk_id,
        )
        for key in ordered[:top_k]
    ]


class HybridRrfRetriever:
    strategy_name = "hybrid_rrf"

    def __init__(
        self,
        dense: RetrievalStrategy,
        sparse: RetrievalStrategy,
        *,
        rrf_k: int,
        top_k: int,
        allow_sparse_failure: bool = True,
    ) -> None:
        self.dense = dense
        self.sparse = sparse
        self.rrf_k = rrf_k
        self.top_k = top_k
        self.allow_sparse_failure = allow_sparse_failure

    def retrieve(
        self, query_vector: list[float], *, query_text: str | None = None
    ) -> list[RetrievedChunk]:
        dense_results = self.dense.retrieve(query_vector, query_text=query_text)
        try:
            sparse_results = self.sparse.retrieve(query_vector, query_text=query_text)
        except Exception:
            if not self.allow_sparse_failure:
                raise
            return dense_results[: self.top_k]
        return reciprocal_rank_fusion(
            [dense_results, sparse_results], rrf_k=self.rrf_k, top_k=self.top_k
        )


class BgeReranker:
    def __init__(
        self,
        model_name: str,
        *,
        batch_size: int,
        device: str = "cpu",
        model_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self.device = device
        self._model_factory = model_factory
        self._model: Any | None = None

    def _get_model(self) -> Any:
        if self._model is None:
            if self._model_factory is None:
                from sentence_transformers import CrossEncoder

                self._model_factory = CrossEncoder
            with HEAVY_MODEL_LOCK:
                get_embedding_service().release_model()
                gc.collect()
                self._model = self._model_factory(self.model_name, device=self.device)
        return self._model

    def rerank(
        self, query: str, candidates: Sequence[RetrievedChunk], *, top_k: int
    ) -> list[RetrievedChunk]:
        if not candidates or not query.strip():
            return []
        model = self._get_model()
        with HEAVY_MODEL_LOCK:
            raw_scores = model.predict(
                [(query, item.content) for item in candidates],
                batch_size=self.batch_size,
                show_progress_bar=False,
            )
        scored = [
            (float(score), _chunk_key(item), item)
            for score, item in zip(raw_scores, candidates, strict=True)
        ]
        scored.sort(key=lambda value: (-value[0], value[1]))
        return [
            RetrievedChunk(
                content=item.content,
                distance=-score,
                source=item.source,
                chunk_id=item.chunk_id,
            )
            for score, _key, item in scored[:top_k]
        ]


class HybridRerankRetriever:
    strategy_name = "hybrid_rerank"

    def __init__(
        self,
        hybrid: RetrievalStrategy,
        reranker: BgeReranker,
        *,
        top_k: int,
        allow_reranker_failure: bool = True,
    ) -> None:
        self.hybrid = hybrid
        self.reranker = reranker
        self.top_k = top_k
        self.allow_reranker_failure = allow_reranker_failure
        self.last_rerank_seconds = 0.0

    def retrieve(
        self, query_vector: list[float], *, query_text: str | None = None
    ) -> list[RetrievedChunk]:
        candidates = self.hybrid.retrieve(query_vector, query_text=query_text)
        started = time.perf_counter()
        try:
            return self.reranker.rerank(query_text or "", candidates, top_k=self.top_k)
        except Exception:
            if not self.allow_reranker_failure:
                raise
            return candidates[: self.top_k]
        finally:
            self.last_rerank_seconds = time.perf_counter() - started


class FallbackRetriever:
    def __init__(self, primary: RetrievalStrategy, fallback: RetrievalStrategy) -> None:
        self.primary = primary
        self.fallback = fallback
        self.strategy_name = getattr(primary, "strategy_name", "advanced")

    def retrieve(
        self, query_vector: list[float], *, query_text: str | None = None
    ) -> list[RetrievedChunk]:
        try:
            return self.primary.retrieve(query_vector, query_text=query_text)
        except Exception:
            return self.fallback.retrieve(query_vector, query_text=query_text)


def _retrieved_chunk(
    chunk: DocumentChunk, document: Document, distance: float
) -> RetrievedChunk:
    metadata = chunk.chunk_metadata or {}
    return RetrievedChunk(
        content=chunk.content,
        distance=distance,
        source=RagSource(
            document_id=document.id,
            title=_string(metadata.get("title")) or document.title,
            category=_string(metadata.get("category")),
            source_name=_string(metadata.get("source_name")) or document.source_name,
            article_id=_string(metadata.get("article_id")),
            page=chunk.page_number,
        ),
        chunk_id=chunk.id,
    )


def _chunk_key(chunk: RetrievedChunk) -> str:
    if chunk.chunk_id is not None:
        return str(chunk.chunk_id)
    return f"{chunk.source.document_id}:{chunk.source.article_id or ''}:{chunk.content}"


def _explain(session: Session, query_vector: list[float], top_k: int) -> dict[str, Any]:
    vector_literal = "[" + ",".join(str(float(value)) for value in query_vector) + "]"
    plan = session.execute(
        text(
            """
            EXPLAIN (FORMAT JSON)
            SELECT dc.id
            FROM document_chunks AS dc
            JOIN documents AS d ON d.id = dc.document_id
            WHERE d.approval_status = 'APPROVED'
              AND d.ingestion_status = 'COMPLETED'
            ORDER BY dc.embedding <=> CAST(:query_vector AS vector)
            LIMIT :top_k
            """
        ),
        {"query_vector": vector_literal, "top_k": top_k},
    ).scalar_one()
    return plan[0] if isinstance(plan, list) else plan


def _string(value: object) -> str | None:
    if isinstance(value, (str, int)):
        return str(value)
    return None
