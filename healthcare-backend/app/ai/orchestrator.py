"""Unified Phase 10 orchestration: risk first, then RAG or business tools."""

from __future__ import annotations

import asyncio
import logging
import re

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
MAX_TOOL_ROUNDS = 6
UUID_PATTERN = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}"
)

RISK_WARNING = (
    "Đây là cảnh báo an toàn, không phải chẩn đoán. Nội dung bạn mô tả có dấu hiệu "
    "có thể cần trợ giúp y tế khẩn cấp. Hãy liên hệ dịch vụ cấp cứu tại nơi bạn đang "
    "ở hoặc đến cơ sở y tế gần nhất ngay; nếu có thể, hãy nhờ một người ở gần hỗ trợ. "
    "Đừng chờ chatbot phản hồi để tìm trợ giúp."
)


def _user_facing_tool_answer(value: str) -> str:
    """Keep technical database identifiers out of chatbot prose."""
    cleaned = re.sub(
        rf"(?im)^\s*[-*]?\s*(?:\*\*)?Mã\s+(?:slot|khung giờ)(?:\*\*)?\s*:\s*`?{UUID_PATTERN.pattern}`?\s*$",
        "",
        value,
    )
    cleaned = re.sub(rf"\s*\(`?{UUID_PATTERN.pattern}`?\)", "", cleaned)
    cleaned = re.sub(rf"`?{UUID_PATTERN.pattern}`?", "", cleaned)
    visible_lines = []
    for line in cleaned.splitlines():
        plain_line = line.replace("*", "").replace("`", "").casefold()
        if re.search(r"mã\s+(?:slot|khung giờ)\s*:", plain_line):
            continue
        if line.strip():
            visible_lines.append(line.rstrip())
    return "\n".join(visible_lines).strip()


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
        results: list[ToolResult] = []
        seen_calls: set[tuple[str, str]] = set()

        for _round in range(MAX_TOOL_ROUNDS):
            if not turn.calls:
                return ChatResponse(
                    answer=_user_facing_tool_answer(turn.text) if turn.text else (
                        "Mình chưa lấy được dữ liệu nghiệp vụ xác thực. Bạn có thể mô tả "
                        "vị trí khó chịu và thời gian muốn khám; không cần biết trước chuyên khoa."
                    ),
                    tool_results=results,
                )

            round_results: list[ToolResult] = []
            for call in turn.calls:
                signature = (call.name, repr(sorted(call.arguments.items())))
                if signature in seen_calls:
                    return ChatResponse(
                        answer=(
                            "Mình chưa thể thu hẹp thêm lựa chọn từ dữ liệu hiện có. "
                            "Bạn hãy bổ sung thời gian muốn khám hoặc dùng màn hình tìm lịch trống."
                        ),
                        tool_results=results,
                    )
                seen_calls.add(signature)
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
                round_results.append(result)
                results.append(result)

            confirmations = [
                BookingConfirmation.model_validate(result.data)
                for result in round_results
                if result.status == "CONFIRMATION_REQUIRED"
            ]
            if confirmations:
                # The signed confirmation endpoint remains the only booking mutation path.
                return ChatResponse(
                    answer=(
                        "Tôi đã tìm một lịch phù hợp. Vui lòng kiểm tra bác sĩ và thời gian "
                        "bên dưới, sau đó bấm Xác nhận đặt lịch nếu thông tin chính xác."
                    ),
                    tool_results=results,
                    booking_confirmation=confirmations[0],
                )

            if any(result.name == "handoff_to_staff" for result in round_results):
                return ChatResponse(
                    answer="Yêu cầu đã được chuyển cho nhân viên và đang chờ tiếp nhận.",
                    tool_results=results,
                )

            slot_results = [
                result for result in round_results if result.name == "available_slots"
            ]
            if slot_results and all(result.data.get("count") == 0 for result in slot_results):
                slot_data = slot_results[0].data
                period_labels = {
                    "MORNING": "buổi sáng",
                    "AFTERNOON": "buổi chiều",
                    "EVENING": "buổi tối",
                    "ALL": "cả ngày",
                }
                period = period_labels.get(str(slot_data.get("period")), "thời gian này")
                date_value = slot_data.get("date")
                date_text = f" ngày {date_value}" if date_value else ""
                return ChatResponse(
                    answer=(
                        f"Hiện không có lịch trống {period}{date_text} trong chuyên khoa phù hợp. "
                        "Bạn có thể yêu cầu tìm ngày hoặc buổi khác."
                    ),
                    tool_results=results,
                )

            turn = await self.gemini.continue_tool_turn(
                turn,
                [result.model_dump(mode="json") for result in round_results],
                GEMINI_TOOL,
            )

        return ChatResponse(
            answer=(
                "Tôi đã tra cứu nhưng chưa thể hoàn tất việc chọn lịch một cách an toàn. "
                "Bạn có thể chọn một trong các kết quả đã hiển thị hoặc dùng màn hình tìm lịch trống."
            ),
            tool_results=results,
        )

