"""Central retrieval strategy construction with Phase 8 exact fallback."""

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.rag.retrieval import (
    BgeReranker,
    Bm25Retriever,
    ExactDenseRetriever,
    FallbackRetriever,
    HnswDenseRetriever,
    HybridRerankRetriever,
    HybridRrfRetriever,
    RetrievalStrategy,
)


def build_retriever(
    session: Session,
    settings: Settings,
    *,
    strategy: str | None = None,
    experiment_mode: bool = False,
) -> RetrievalStrategy:
    selected = strategy or settings.rag_strategy
    exact = ExactDenseRetriever(
        session,
        top_k=settings.rag_top_k,
        max_distance=settings.rag_max_cosine_distance,
    )
    if selected == "exact_dense":
        return exact

    dense_top_k = settings.rag_dense_candidates
    hnsw = HnswDenseRetriever(
        session,
        top_k=dense_top_k if selected.startswith("hybrid") else settings.rag_top_k,
        max_distance=2.0 if selected.startswith("hybrid") else settings.rag_max_cosine_distance,
        ef_search=settings.rag_hnsw_ef_search,
    )
    if selected == "hnsw_dense":
        return hnsw if experiment_mode else FallbackRetriever(hnsw, exact)

    sparse = Bm25Retriever(
        session,
        top_k=settings.rag_sparse_candidates,
        k1=settings.rag_bm25_k1,
        b=settings.rag_bm25_b,
    )
    hybrid_top_k = (
        settings.rag_rerank_candidates
        if selected == "hybrid_rerank"
        else settings.rag_top_k
    )
    hybrid = HybridRrfRetriever(
        hnsw,
        sparse,
        rrf_k=settings.rag_rrf_k,
        top_k=hybrid_top_k,
        allow_sparse_failure=not experiment_mode,
    )
    if selected == "hybrid_rrf":
        return hybrid if experiment_mode else FallbackRetriever(hybrid, exact)
    if selected == "hybrid_rerank":
        reranked = HybridRerankRetriever(
            hybrid,
            BgeReranker(
                settings.rag_reranker_model,
                batch_size=settings.rag_reranker_batch_size,
                device=settings.rag_reranker_device,
            ),
            top_k=settings.rag_top_k,
            allow_reranker_failure=not experiment_mode,
        )
        return reranked if experiment_mode else FallbackRetriever(reranked, exact)
    raise ValueError(f"Unsupported RAG strategy: {selected}")
