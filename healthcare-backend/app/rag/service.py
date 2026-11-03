"""RAG V1 orchestration without tools or access to private clinical data."""

from __future__ import annotations

import asyncio

from app.ai.gemini_client import GeminiClient
from app.ai.schemas import ChatHistoryItem, ChatResponse
from app.core.errors import ApplicationError
from app.documents.embeddings import EmbeddingError, EmbeddingService
from app.rag.retrieval import RetrievalStrategy
from app.rag.schemas import RetrievedChunk

NO_CONTEXT_ANSWER = (
    "Hiện mình chưa tìm thấy đủ thông tin phù hợp trong nguồn dữ liệu đã được phê duyệt. "
    "Bạn nên trao đổi với bác sĩ hoặc nhân viên y tế nếu cần đánh giá chuyên môn."
)


class RagService:
    def __init__(
        self,
        embeddings: EmbeddingService,
        retriever: RetrievalStrategy,
        gemini: GeminiClient,
    ) -> None:
        self.embeddings = embeddings
        self.retriever = retriever
        self.gemini = gemini

    async def retrieve(self, question: str) -> list[RetrievedChunk]:
        try:
            query_vector = (await asyncio.to_thread(self.embeddings.embed, [question]))[0]
            return self.retriever.retrieve(query_vector, query_text=question)
        except (EmbeddingError, ValueError) as exc:
            raise ApplicationError(
                503,
                "rag_unavailable",
                "Knowledge retrieval is temporarily unavailable. Please use the manual features.",
            ) from exc
        except Exception as exc:
            raise ApplicationError(
                503,
                "rag_unavailable",
                "Knowledge retrieval is temporarily unavailable. Please use the manual features.",
            ) from exc

    async def answer(
        self, question: str, history: list[ChatHistoryItem]
    ) -> ChatResponse:
        chunks = await self.retrieve(question)
        if not chunks:
            return ChatResponse(answer=NO_CONTEXT_ANSWER, sources=[])
        context = "\n\n".join(
            f"[Nguồn {index}]\n{chunk.content}" for index, chunk in enumerate(chunks, 1)
        )
        answer = await self.gemini.generate_grounded_reply(question, history, context)
        return ChatResponse(answer=answer, sources=[chunk.source for chunk in chunks])
