"""Real PostgreSQL HNSW plan check; opt in with RUN_DB_INTEGRATION=1."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import select

from app.core.database import get_session_factory
from app.models.knowledge import DocumentChunk
from app.rag.retrieval import ExactDenseRetriever, HnswDenseRetriever


@pytest.mark.skipif(
    os.getenv("RUN_DB_INTEGRATION") != "1",
    reason="Set RUN_DB_INTEGRATION=1 to test the real development database",
)
def test_exact_and_hnsw_use_expected_plans_and_return_top_k() -> None:
    with get_session_factory()() as session:
        vector = session.scalar(select(DocumentChunk.embedding).limit(1))
        assert vector is not None
        query = list(vector)
        exact = ExactDenseRetriever(session, top_k=5, max_distance=2.0)
        exact_results = exact.retrieve(query)
        exact_plan = exact.explain_exact(query)
        assert exact_results
        assert exact.uses_hnsw(exact_plan) is False
        session.rollback()

        hnsw = HnswDenseRetriever(
            session, top_k=5, max_distance=2.0, ef_search=40
        )
        hnsw_results = hnsw.retrieve(query)
        hnsw_plan = hnsw.explain_hnsw(query)
        assert 1 <= len(hnsw_results) <= 5
        assert exact.uses_hnsw(hnsw_plan) is True
