"""HTTP layer for the Phase 7 chatbot extended with Phase 8 RAG."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.ai.chat_service import ChatService
from app.ai.gemini_client import GeminiClient
from app.ai.schemas import ChatRequest, ChatResponse
from app.ai.schemas import BookingConfirmationResponse
from app.ai.orchestrator import ChatOrchestrator
from app.ai.tools.executor import ToolExecutor
from app.ai.tools.schemas import ConfirmBookingRequest
from app.auth.context import ActorContext
from app.auth.dependencies import get_current_actor
from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import enforce_rate_limit
from app.documents.embeddings import get_embedding_service
from app.rag.factory import build_retriever
from app.rag.service import RagService

router = APIRouter(prefix="/chat", tags=["Chatbot"])


def get_chat_service(db: Annotated[Session, Depends(get_db)]) -> ChatService:
    settings = get_settings()
    gemini = GeminiClient(settings)
    embeddings = get_embedding_service()
    retriever = build_retriever(db, settings)
    rag = RagService(embeddings, retriever, gemini)
    tools = ToolExecutor(db, settings)
    orchestrator = ChatOrchestrator(gemini, rag, tools, settings)
    return ChatService(gemini, rag, orchestrator)


def get_tool_executor(db: Annotated[Session, Depends(get_db)]) -> ToolExecutor:
    return ToolExecutor(db, get_settings())


@router.post("/messages", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    http_request: Request,
    actor: Annotated[ActorContext, Depends(get_current_actor)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    settings = get_settings()
    enforce_rate_limit(
        http_request,
        scope="chat_message",
        identity=str(actor.user_id),
        limit=settings.chat_rate_limit,
        window_seconds=settings.common_rate_window_seconds,
        enabled=settings.rate_limit_enabled,
    )
    return await service.reply(request, actor)


@router.post("/bookings/confirm", response_model=BookingConfirmationResponse)
def confirm_booking(
    request: ConfirmBookingRequest,
    actor: Annotated[ActorContext, Depends(get_current_actor)],
    tools: Annotated[ToolExecutor, Depends(get_tool_executor)],
) -> BookingConfirmationResponse:
    appointment = tools.confirm_booking(request.confirmation_token, actor)
    return BookingConfirmationResponse(
        appointment_id=appointment.id,
        slot_id=appointment.schedule_slot_id,
    )
