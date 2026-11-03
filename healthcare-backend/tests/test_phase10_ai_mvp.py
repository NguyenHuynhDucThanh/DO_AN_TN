"""Phase 10 unified routing and deterministic Risk Alert tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.ai.gemini_client import GeminiFunctionCall, GeminiToolTurn
from app.ai.orchestrator import ChatOrchestrator, RISK_WARNING
from app.ai.risk.service import RiskAlertService
from app.ai.routing import ChatIntentRouter, ChatRoute
from app.ai.schemas import ChatRequest, ChatResponse, ToolResult
from app.ai.tools.executor import ToolExecutor
from app.auth.context import ActorContext
from app.core.config import Settings
from app.core.errors import ApplicationError
from app.models.enums import HandoffPriority, HandoffStatus
from app.rag.schemas import RagSource


def settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql+psycopg://unit:unit@localhost/unit",
        jwt_secret="phase-10-unit-test-secret-with-32-characters",
        gemini_api_key="synthetic",
        gemini_model="synthetic-model",
    )


def actor() -> ActorContext:
    return ActorContext(uuid4(), frozenset({"PATIENT"}))


@pytest.mark.parametrize(
    ("message", "expected_code"),
    [
        ("Tôi không thở được", "RISK-RESPIRATORY"),
        ("Đau ngực dữ dội", "RISK-CHEST"),
        ("Tôi bị liệt nửa người", "RISK-STROKE"),
        ("Đang chảy máu không cầm", "RISK-BLEEDING"),
        ("Người bên cạnh bất tỉnh", "RISK-CONSCIOUSNESS"),
        ("Tôi nghi bị ngộ độc", "RISK-POISONING"),
        ("Tôi muốn tự tử", "RISK-SELF-HARM"),
    ],
)
def test_risk_alert_positive_fixed_scenarios(message: str, expected_code: str) -> None:
    assessment = RiskAlertService().assess(message)
    assert assessment is not None
    assert expected_code in assessment.rule_codes


@pytest.mark.parametrize(
    "message",
    [
        "Tôi hơi đau đầu sau khi làm việc",
        "Tôi không bị đau ngực dữ dội",
        "Dấu hiệu bất tỉnh là gì?",
        "Tôi đang tìm hiểu về ngộ độc",
        "Không thở được là gì?",
        "Bài viết về dấu hiệu muốn tự tử là gì?",
    ],
)
def test_risk_alert_negative_and_false_positive_cases(message: str) -> None:
    assert RiskAlertService().assess(message) is None


@pytest.mark.parametrize(
    ("message", "route"),
    [
        ("Viêm họng là gì?", ChatRoute.KNOWLEDGE),
        ("Tìm bác sĩ tim mạch", ChatRoute.BUSINESS_LOOKUP),
        ("Tôi muốn đặt lịch khám", ChatRoute.BOOKING),
        ("Chuyển tôi tới nhân viên hỗ trợ", ChatRoute.HANDOFF),
    ],
)
def test_deterministic_top_level_routing(message: str, route: ChatRoute) -> None:
    assert ChatIntentRouter().route(message) == route


@pytest.mark.anyio
async def test_risk_runs_before_rag_gemini_and_creates_priority_handoff() -> None:
    gemini = MagicMock()
    gemini.request_tool_turn = AsyncMock()
    rag = MagicMock()
    rag.answer = AsyncMock()
    tools = MagicMock()
    tools.create_risk_handoff = AsyncMock(return_value=ToolResult(
        name="risk_handoff",
        status="SUCCESS",
        data={
            "handoff_id": str(uuid4()),
            "status": "PENDING",
            "priority": "URGENT",
        },
    ))
    response = await ChatOrchestrator(gemini, rag, tools, settings()).reply(
        ChatRequest(message="Tôi không thở được"), actor()
    )
    assert response.answer == RISK_WARNING
    assert response.risk_alert is not None
    assert response.risk_alert.level == "URGENT"
    assert response.risk_alert.handoff.status == "PENDING"
    assert "không phải chẩn đoán" in response.answer
    rag.answer.assert_not_awaited()
    gemini.request_tool_turn.assert_not_awaited()


@pytest.mark.anyio
async def test_risk_warning_survives_handoff_failure() -> None:
    tools = MagicMock()
    tools.create_risk_handoff = AsyncMock(side_effect=RuntimeError("private database error"))
    response = await ChatOrchestrator(MagicMock(), MagicMock(), tools, settings()).reply(
        ChatRequest(message="Đang chảy máu không cầm"), actor()
    )
    assert response.risk_alert is not None
    assert response.risk_alert.handoff.status == "FAILED"
    assert "private" not in response.model_dump_json().lower()


@pytest.mark.anyio
async def test_knowledge_route_uses_rag_and_preserves_sources() -> None:
    source = RagSource(document_id=uuid4(), title="Nguồn thật")
    rag = MagicMock()
    rag.answer = AsyncMock(return_value=ChatResponse(answer="Theo nguồn đã duyệt", sources=[source]))
    gemini = MagicMock()
    gemini.request_tool_turn = AsyncMock()
    response = await ChatOrchestrator(gemini, rag, MagicMock(), settings()).reply(
        ChatRequest(message="Viêm họng là gì?"), actor()
    )
    assert response.sources == [source]
    rag.answer.assert_awaited_once()
    gemini.request_tool_turn.assert_not_awaited()


@pytest.mark.anyio
async def test_doctor_query_skips_rag_and_uses_tool_path() -> None:
    gemini = MagicMock()
    gemini.request_tool_turn = AsyncMock(return_value=GeminiToolTurn(
        text=None,
        calls=[GeminiFunctionCall("search_specialty", {"query": "tim mạch"})],
        contents=[],
        model_content=MagicMock(),
    ))
    gemini.complete_tool_turn = AsyncMock(return_value="Có chuyên khoa Tim mạch.")
    tools = MagicMock()
    tools.execute = AsyncMock(return_value=ToolResult(
        name="search_specialty", status="SUCCESS", data={"items": [], "count": 0}
    ))
    rag = MagicMock()
    rag.answer = AsyncMock()
    response = await ChatOrchestrator(gemini, rag, tools, settings()).reply(
        ChatRequest(message="Tìm bác sĩ chuyên khoa tim mạch"), actor()
    )
    assert response.tool_results[0].name == "search_specialty"
    assert response.sources == []
    rag.answer.assert_not_awaited()


@pytest.mark.anyio
async def test_tool_failure_is_controlled_and_not_reported_as_success() -> None:
    gemini = MagicMock()
    gemini.request_tool_turn = AsyncMock(return_value=GeminiToolTurn(
        text=None,
        calls=[GeminiFunctionCall("available_slots", {"doctor_id": str(uuid4()), "date": "2035-01-01"})],
        contents=[],
        model_content=MagicMock(),
    ))
    tools = MagicMock()
    tools.execute = AsyncMock(side_effect=ApplicationError(503, "tool_unavailable", "Safe error"))
    with pytest.raises(ApplicationError) as caught:
        await ChatOrchestrator(gemini, MagicMock(), tools, settings()).reply(
            ChatRequest(message="Bác sĩ này còn slot ngày mai không?"), actor()
        )
    assert caught.value.code == "tool_unavailable"


@pytest.mark.anyio
async def test_risk_handoff_adapter_reuses_handoff_service_without_raw_message() -> None:
    tools = ToolExecutor.__new__(ToolExecutor)
    tools.handoffs = MagicMock()
    ticket = SimpleNamespace(
        id=uuid4(), status=HandoffStatus.PENDING, priority=HandoffPriority.URGENT
    )
    tools.handoffs.create_risk_alert.return_value = ticket
    current_actor = actor()
    result = await tools.create_risk_handoff(("RISK-RESPIRATORY",), current_actor)
    tools.handoffs.create_risk_alert.assert_called_once_with(
        ("RISK-RESPIRATORY",), current_actor
    )
    assert result.data["priority"] == "URGENT"


def test_phase10_ai_source_has_no_medical_record_dependency() -> None:
    root = Path(__file__).resolve().parents[1] / "app" / "ai"
    source = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in root.rglob("*.py")
    )
    assert "app.medical_records" not in source
    assert "app.models.medical_record" not in source
    assert "get_medical_record" not in source

