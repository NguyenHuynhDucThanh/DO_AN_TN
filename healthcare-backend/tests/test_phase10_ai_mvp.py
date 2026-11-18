"""Phase 10 unified routing and deterministic Risk Alert tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.ai.gemini_client import GeminiFunctionCall, GeminiToolTurn
from app.ai.orchestrator import ChatOrchestrator, RISK_WARNING, _user_facing_tool_answer
from app.ai.risk.service import RiskAlertService
from app.ai.routing import ChatIntentRouter, ChatRoute
from app.ai.schemas import ChatRequest, ChatResponse, ToolResult
from app.ai.tools.executor import ToolExecutor
from app.auth.context import ActorContext
from app.core.config import Settings
from app.core.errors import ApplicationError
from app.models.enums import HandoffPriority, HandoffStatus
from app.rag.schemas import RagSource, RetrievedChunk
from app.rag.service import _unique_sources


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


def test_tool_answer_hides_internal_slot_uuid() -> None:
    slot_id = uuid4()
    answer = _user_facing_tool_answer(
        f"- **Thời gian:** 08:30 - 09:00\n- **Mã slot:** `{slot_id}`\n- 09:00 - 09:30 (`{slot_id}`)"
    )
    assert str(slot_id) not in answer
    assert "Mã slot" not in answer
    assert "08:30 - 09:00" in answer
    assert "09:00 - 09:30" in answer


def test_rag_sources_are_deduplicated_for_display() -> None:
    source = RagSource(document_id=uuid4(), title="Nguồn y khoa")
    duplicate_title = RagSource(document_id=uuid4(), title="Nguồn y khoa")
    chunks = [
        RetrievedChunk(content="Đoạn một", distance=0.1, source=source, chunk_id=uuid4()),
        RetrievedChunk(content="Đoạn hai", distance=0.2, source=duplicate_title, chunk_id=uuid4()),
    ]
    assert _unique_sources(chunks) == [source]


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
        ("Tôi đau bụng và muốn khám vào sáng mai", ChatRoute.BOOKING),
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
    gemini.continue_tool_turn = AsyncMock(return_value=GeminiToolTurn(
        text="Có chuyên khoa Tim mạch.",
        calls=[],
        contents=[],
        model_content=MagicMock(),
    ))
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
    assert response.answer == "Có chuyên khoa Tim mạch."
    assert response.sources == []
    rag.answer.assert_not_awaited()


@pytest.mark.anyio
async def test_symptom_and_time_can_reach_booking_confirmation_without_known_specialty() -> None:
    specialty_id = uuid4()
    doctor_id = uuid4()
    slot_id = uuid4()
    confirmation = {
        "status": "CONFIRMATION_REQUIRED",
        "confirmation_token": "x" * 30,
        "slot_id": str(slot_id),
        "doctor_id": str(doctor_id),
        "doctor_name": "Bác sĩ Demo",
        "specialty_id": str(specialty_id),
        "specialty_name": "Nội tổng quát",
        "start_at": "2035-01-02T01:00:00Z",
        "end_at": "2035-01-02T01:30:00Z",
    }
    turns = [
        GeminiToolTurn(
            text=None,
            calls=[GeminiFunctionCall("list_doctors", {"specialty_id": str(specialty_id)})],
            contents=[],
            model_content=MagicMock(),
        ),
        GeminiToolTurn(
            text=None,
            calls=[GeminiFunctionCall(
                "available_slots", {"doctor_id": str(doctor_id), "date": "2035-01-02"}
            )],
            contents=[],
            model_content=MagicMock(),
        ),
        GeminiToolTurn(
            text=None,
            calls=[GeminiFunctionCall("create_booking", {"slot_id": str(slot_id)})],
            contents=[],
            model_content=MagicMock(),
        ),
    ]
    gemini = MagicMock()
    gemini.request_tool_turn = AsyncMock(return_value=GeminiToolTurn(
        text=None,
        calls=[GeminiFunctionCall("search_specialty", {"query": "Nội tổng quát"})],
        contents=[],
        model_content=MagicMock(),
    ))
    gemini.continue_tool_turn = AsyncMock(side_effect=turns)
    tools = MagicMock()
    tools.execute = AsyncMock(side_effect=[
        ToolResult(name="search_specialty", status="SUCCESS", data={
            "items": [{"id": str(specialty_id), "name": "Nội tổng quát"}], "count": 1
        }),
        ToolResult(name="list_doctors", status="SUCCESS", data={
            "items": [{"id": str(doctor_id), "full_name": "Bác sĩ Demo"}], "count": 1
        }),
        ToolResult(name="available_slots", status="SUCCESS", data={
            "items": [{"slot_id": str(slot_id), "doctor_id": str(doctor_id)}], "count": 1
        }),
        ToolResult(name="create_booking", status="CONFIRMATION_REQUIRED", data=confirmation),
    ])

    response = await ChatOrchestrator(gemini, MagicMock(), tools, settings()).reply(
        ChatRequest(message="Tôi đau bụng và muốn khám vào sáng mai"), actor()
    )

    assert [result.name for result in response.tool_results] == [
        "search_specialty", "list_doctors", "available_slots", "create_booking"
    ]
    assert response.booking_confirmation is not None
    assert response.booking_confirmation.slot_id == slot_id
    assert tools.execute.await_count == 4


@pytest.mark.anyio
async def test_empty_specialty_slots_stop_with_clear_period_message() -> None:
    specialty_id = uuid4()
    gemini = MagicMock()
    gemini.request_tool_turn = AsyncMock(return_value=GeminiToolTurn(
        text=None,
        calls=[GeminiFunctionCall("available_slots", {
            "specialty_id": str(specialty_id),
            "date": "2035-01-02",
            "period": "MORNING",
        })],
        contents=[],
        model_content=MagicMock(),
    ))
    gemini.continue_tool_turn = AsyncMock()
    tools = MagicMock()
    tools.execute = AsyncMock(return_value=ToolResult(
        name="available_slots",
        status="SUCCESS",
        data={"items": [], "count": 0, "date": "2035-01-02", "period": "MORNING"},
    ))

    response = await ChatOrchestrator(gemini, MagicMock(), tools, settings()).reply(
        ChatRequest(message="Tôi muốn khám vào sáng mai"), actor()
    )

    assert "không có lịch trống buổi sáng ngày 2035-01-02" in response.answer
    gemini.continue_tool_turn.assert_not_awaited()


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

