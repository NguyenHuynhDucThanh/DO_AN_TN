"""Unified Phase 10 orchestration: risk first, then RAG or business tools."""

from __future__ import annotations

import asyncio
import logging

from app.ai.errors import ChatbotUnavailableError
from app.ai.gemini_client import GeminiClient
from app.ai.risk.service import RiskAlertService
from app.ai.routing import ChatIntentRouter, ChatRoute
from app.ai.schemas import (
    BookingConfirmation,
    ChatRequest,
    ChatResponse,
    RiskAlert,
    RiskHandoff,
    ToolResult,
)
from app.ai.tools.executor import ToolExecutor
from app.ai.tools.registry import GEMINI_TOOL
from app.auth.context import ActorContext
from app.core.config import Settings
from app.rag.service import RagService

logger = logging.getLogger(__name__)

RISK_WARNING = (
    "Đây là cảnh báo an toàn, không phải chẩn đoán. Nội dung bạn mô tả có dấu hiệu "
    "có thể cần trợ giúp y tế khẩn cấp. Hãy liên hệ dịch vụ cấp cứu tại nơi bạn đang "
    "ở hoặc đến cơ sở y tế gần nhất ngay; nếu có thể, hãy nhờ một người ở gần hỗ trợ. "
    "Đừng chờ chatbot phản hồi để tìm trợ giúp."
)


class ChatOrchestrator:
    def __init__(
        self,
        gemini: GeminiClient,
        rag: RagService | None,
        tools: ToolExecutor,
        settings: Settings,
        risk_service: RiskAlertService | None = None,
        intent_router: ChatIntentRouter | None = None,
    ) -> None:
        self.gemini = gemini
        self.rag = rag
        self.tools = tools
        self.timeout_seconds = settings.tool_timeout_seconds
        self.risk_service = risk_service or RiskAlertService()
        self.intent_router = intent_router or ChatIntentRouter()

    async def reply(self, request: ChatRequest, actor: ActorContext) -> ChatResponse:
        assessment = self.risk_service.assess(request.message)
        if assessment is not None:
            return await self._risk_response(assessment.rule_codes, actor)

        route = self.intent_router.route(request.message)
        if route == ChatRoute.KNOWLEDGE:
            if request.use_rag and self.rag is not None:
                return await self.rag.answer(request.message, request.history)
            answer = await self.gemini.generate_reply(request.message, request.history)
            return ChatResponse(answer=answer)

        return await self._business_response(request, actor)

    async def _risk_response(
        self, rule_codes: tuple[str, ...], actor: ActorContext
    ) -> ChatResponse:
        tool_results: list[ToolResult] = []
        try:
            handoff_result = await asyncio.wait_for(
                self.tools.create_risk_handoff(rule_codes, actor),
                timeout=self.timeout_seconds,
            )
            tool_results.append(handoff_result)
            handoff = RiskHandoff(
                status="PENDING",
                handoff_id=handoff_result.data["handoff_id"],
                message="Yêu cầu hỗ trợ ưu tiên đã được ghi nhận; việc này không thay thế cấp cứu.",
            )
        except Exception:
            # A handoff outage must never suppress the deterministic safety warning.
            logger.warning("Risk handoff creation failed")
            handoff = RiskHandoff(
                status="FAILED",
                message=(
                    "Chưa thể ghi nhận yêu cầu hỗ trợ. Hãy dùng chức năng liên hệ thủ công "
                    "và tìm trợ giúp y tế ngay."
                ),
            )
        risk_alert = RiskAlert(
            title="Cảnh báo an toàn khẩn cấp",
            message=RISK_WARNING,
            recommended_actions=[
                "Liên hệ dịch vụ cấp cứu tại nơi bạn đang ở hoặc đến cơ sở y tế gần nhất.",
                "Nhờ một người ở gần hỗ trợ nếu có thể.",
                "Không chờ chatbot và không tự chẩn đoán hoặc tự điều trị.",
            ],
            rule_codes=list(rule_codes),
            handoff=handoff,
        )
        return ChatResponse(
            answer=RISK_WARNING,
            tool_results=tool_results,
            risk_alert=risk_alert,
        )

    async def _business_response(
        self, request: ChatRequest, actor: ActorContext
    ) -> ChatResponse:
        turn = await self.gemini.request_tool_turn(
            request.message, request.history, None, GEMINI_TOOL
        )
        if not turn.calls:
            return ChatResponse(
                answer=(
                    "Mình chưa lấy được dữ liệu nghiệp vụ xác thực. Bạn hãy nêu rõ chuyên khoa, "
                    "bác sĩ, ngày muốn xem lịch hoặc dùng màn hình đặt lịch trực tiếp."
                )
            )

        results: list[ToolResult] = []
        for call in turn.calls:
            try:
                result = await asyncio.wait_for(
                    self.tools.execute(call.name, call.arguments, actor),
                    timeout=self.timeout_seconds,
                )
            except (asyncio.TimeoutError, TimeoutError):
                raise ChatbotUnavailableError(
                    "The requested healthcare action took too long. Please try again.",
                    "tool_timeout",
                ) from None
            results.append(result)

        confirmations = [
            BookingConfirmation.model_validate(result.data)
            for result in results
            if result.status == "CONFIRMATION_REQUIRED"
        ]
        if confirmations:
            # Mutations never follow free-form text. The dedicated HTTP endpoint is
            # the only path that can consume this signed confirmation.
            confirmation = confirmations[0]
            return ChatResponse(
                answer=(
                    "Vui lòng kiểm tra bác sĩ và thời gian bên dưới, sau đó bấm "
                    "Xác nhận đặt lịch nếu thông tin chính xác."
                ),
                tool_results=results,
                booking_confirmation=confirmation,
            )

        if any(result.name == "handoff_to_staff" for result in results):
            return ChatResponse(
                answer="Yêu cầu đã được chuyển cho nhân viên và đang chờ tiếp nhận.",
                tool_results=results,
            )

        answer = await self.gemini.complete_tool_turn(
            turn, [result.model_dump(mode="json") for result in results]
        )
        return ChatResponse(answer=answer, tool_results=results)

