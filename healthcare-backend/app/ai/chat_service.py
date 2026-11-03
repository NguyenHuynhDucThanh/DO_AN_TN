"""Application service reusing Phase 7 chat and optional Phase 8 RAG."""

from app.ai.gemini_client import GeminiClient
from app.ai.schemas import ChatRequest, ChatResponse
from app.ai.orchestrator import ChatOrchestrator
from app.auth.context import ActorContext
from app.rag.service import RagService


class ChatService:
    def __init__(
        self,
        client: GeminiClient,
        rag_service: RagService | None = None,
        orchestrator: ChatOrchestrator | None = None,
    ) -> None:
        self.client = client
        self.rag_service = rag_service
        self.orchestrator = orchestrator

    async def reply(
        self, request: ChatRequest, actor: ActorContext | None = None
    ) -> ChatResponse:
        if self.orchestrator is not None:
            if actor is None:
                raise ValueError("ActorContext is required for tool-enabled chat")
            return await self.orchestrator.reply(request, actor)
        if request.use_rag and self.rag_service is not None:
            return await self.rag_service.answer(request.message, request.history)
        answer = await self.client.generate_reply(request.message, request.history)
        return ChatResponse(answer=answer, sources=[])
