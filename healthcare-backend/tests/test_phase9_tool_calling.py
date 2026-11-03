"""Phase 9 contracts: tools adapt services, identity is server-owned, booking is explicit."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from google.genai import types

from app.ai.errors import ChatbotInvalidResponseError
from app.ai.gemini_client import GeminiClient, GeminiFunctionCall, GeminiToolTurn
from app.ai.orchestrator import ChatOrchestrator
from app.ai.schemas import BookingConfirmation, ChatRequest, ToolResult
from app.ai.tools.confirmation import create_booking_confirmation
from app.ai.tools.executor import ToolExecutor
from app.ai.tools.registry import TOOL_ARGUMENT_MODELS, TOOL_DECLARATIONS
from app.auth.context import ActorContext
from app.core.errors import BadRequestError, ConflictError, ForbiddenError
from app.core.config import Settings
from app.models.enums import HandoffStatus, ScheduleStatus, SlotStatus


def settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url="postgresql+psycopg://unit:unit@localhost/unit",
        jwt_secret="phase-9-unit-test-secret-with-32-characters",
        gemini_api_key="synthetic",
        gemini_model="synthetic-model",
    )


def actor(*roles: str) -> ActorContext:
    return ActorContext(user_id=uuid4(), roles=frozenset(roles))


def executor() -> ToolExecutor:
    instance = ToolExecutor.__new__(ToolExecutor)
    instance.settings = settings()
    instance.specialties = MagicMock()
    instance.doctors = MagicMock()
    instance.schedules = MagicMock()
    instance.appointments = MagicMock()
    instance.handoffs = MagicMock()
    return instance


class FakeGeminiAsyncClient:
    def __init__(self, response):
        self.response = response
        self.calls = []
        self.models = self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class FakeGeminiSdkClient:
    def __init__(self, async_client):
        self.aio = async_client


def slot_fixture():
    specialty = SimpleNamespace(id=uuid4(), name="Tim mạch")
    doctor = SimpleNamespace(
        id=uuid4(),
        user=SimpleNamespace(full_name="Bác sĩ Demo"),
        specialty=specialty,
    )
    schedule = SimpleNamespace(status=ScheduleStatus.ACTIVE, doctor=doctor)
    return SimpleNamespace(
        id=uuid4(),
        status=SlotStatus.AVAILABLE,
        start_at=datetime.now(timezone.utc) + timedelta(days=2),
        end_at=datetime.now(timezone.utc) + timedelta(days=2, minutes=30),
        schedule=schedule,
    )


def test_registry_has_only_srs_tools_and_no_identity_arguments() -> None:
    assert set(TOOL_ARGUMENT_MODELS) == {
        "search_specialty",
        "list_doctors",
        "available_slots",
        "create_booking",
        "handoff_to_staff",
    }
    forbidden = {"user_id", "patient_id", "role", "doctor_identity"}
    for declaration in TOOL_DECLARATIONS:
        schema = declaration.parameters_json_schema
        assert forbidden.isdisjoint(schema.get("properties", {}))
    assert all("medical" not in name for name in TOOL_ARGUMENT_MODELS)


@pytest.mark.anyio
async def test_gemini_structured_tool_request_is_parsed_with_manual_execution() -> None:
    function_call = types.FunctionCall(
        name="search_specialty", args={"query": "tim mạch"}, id="call-1"
    )
    content = types.Content(
        role="model", parts=[types.Part(function_call=function_call)]
    )
    fake = FakeGeminiAsyncClient(SimpleNamespace(
        candidates=[SimpleNamespace(content=content)],
        function_calls=[function_call],
        text=None,
    ))
    client = GeminiClient(settings(), client_factory=lambda **_kwargs: FakeGeminiSdkClient(fake))
    turn = await client.request_tool_turn("Tìm chuyên khoa tim mạch", [], None, MagicMock())
    assert turn.calls == [GeminiFunctionCall("search_specialty", {"query": "tim mạch"}, "call-1")]
    assert fake.calls[0]["config"].automatic_function_calling.disable is True


@pytest.mark.anyio
async def test_gemini_malformed_tool_call_is_controlled() -> None:
    malformed = SimpleNamespace(name="search_specialty", args=object(), id="call-bad")
    fake = FakeGeminiAsyncClient(SimpleNamespace(
        candidates=[SimpleNamespace(content=MagicMock())],
        function_calls=[malformed],
        text=None,
    ))
    client = GeminiClient(settings(), client_factory=lambda **_kwargs: FakeGeminiSdkClient(fake))
    with pytest.raises(ChatbotInvalidResponseError):
        await client.request_tool_turn("Tìm chuyên khoa", [], None, MagicMock())


@pytest.mark.anyio
async def test_specialty_search_reuses_service_and_no_results_are_explicit() -> None:
    tools = executor()
    tools.specialties.search.return_value = []
    result = await tools.execute("search_specialty", {"query": "không có"}, actor("PATIENT"))
    tools.specialties.search.assert_called_once_with("không có")
    assert result.data == {"items": [], "count": 0}


@pytest.mark.anyio
async def test_malformed_unknown_and_identity_spoofing_are_rejected() -> None:
    tools = executor()
    with pytest.raises(BadRequestError) as missing:
        await tools.execute("available_slots", {"doctor_id": str(uuid4())}, actor("PATIENT"))
    assert missing.value.code == "invalid_tool_arguments"
    with pytest.raises(BadRequestError) as blank:
        await tools.execute("search_specialty", {"query": "   "}, actor("PATIENT"))
    assert blank.value.code == "invalid_tool_arguments"
    with pytest.raises(BadRequestError) as unknown:
        await tools.execute("fake_tool", {}, actor("PATIENT"))
    assert unknown.value.code == "unknown_tool"
    with pytest.raises(BadRequestError) as spoof:
        await tools.execute(
            "create_booking",
            {"slot_id": str(uuid4()), "patient_id": str(uuid4()), "role": "ADMIN"},
            actor("PATIENT"),
        )
    assert spoof.value.code == "invalid_tool_arguments"


@pytest.mark.anyio
async def test_booking_tool_never_books_before_explicit_confirmation() -> None:
    tools = executor()
    slot = slot_fixture()
    tools.schedules.get_slot.return_value = slot
    patient = actor("PATIENT")
    result = await tools.execute("create_booking", {"slot_id": str(slot.id)}, patient)
    assert result.status == "CONFIRMATION_REQUIRED"
    assert result.data["slot_id"] == str(slot.id)
    tools.appointments.create.assert_not_called()


@pytest.mark.anyio
async def test_booking_tool_is_patient_only() -> None:
    tools = executor()
    with pytest.raises(ForbiddenError):
        await tools.execute("create_booking", {"slot_id": str(uuid4())}, actor("DOCTOR"))
    tools.schedules.get_slot.assert_not_called()


def test_confirm_booking_is_actor_bound_and_reuses_appointment_service() -> None:
    tools = executor()
    patient = actor("PATIENT")
    slot_id = uuid4()
    token = create_booking_confirmation(patient.user_id, slot_id, tools.settings)
    appointment = SimpleNamespace(id=uuid4(), schedule_slot_id=slot_id)
    tools.appointments.create.return_value = appointment
    assert tools.confirm_booking(token, patient) is appointment
    passed_data, passed_actor = tools.appointments.create.call_args.args
    assert passed_data.schedule_slot_id == slot_id
    assert passed_actor == patient
    with pytest.raises(ForbiddenError) as mismatch:
        tools.confirm_booking(token, actor("PATIENT"))
    assert mismatch.value.code == "confirmation_actor_mismatch"


def test_repeated_confirmation_keeps_service_conflict() -> None:
    tools = executor()
    patient = actor("PATIENT")
    token = create_booking_confirmation(patient.user_id, uuid4(), tools.settings)
    tools.appointments.create.side_effect = ConflictError(
        "The selected slot is already occupied.", "slot_occupied"
    )
    with pytest.raises(ConflictError) as conflict:
        tools.confirm_booking(token, patient)
    assert conflict.value.status_code == 409


@pytest.mark.anyio
async def test_handoff_tool_reuses_existing_service_and_server_identity() -> None:
    tools = executor()
    requester = actor("PATIENT")
    request = SimpleNamespace(id=uuid4(), status=HandoffStatus.PENDING)
    tools.handoffs.create.return_value = request
    result = await tools.execute("handoff_to_staff", {"reason": "Cần nhân viên hỗ trợ"}, requester)
    data, passed_actor = tools.handoffs.create.call_args.args
    assert data.source == "CHATBOT"
    assert passed_actor == requester
    assert result.data["handoff_id"] == str(request.id)


@pytest.mark.anyio
async def test_orchestrator_returns_confirmation_without_model_followup() -> None:
    patient = actor("PATIENT")
    confirmation = BookingConfirmation(
        confirmation_token="x" * 30,
        slot_id=uuid4(),
        doctor_id=uuid4(),
        doctor_name="Bác sĩ Demo",
        specialty_id=uuid4(),
        specialty_name="Tim mạch",
        start_at=datetime.now(timezone.utc) + timedelta(days=1),
        end_at=datetime.now(timezone.utc) + timedelta(days=1, minutes=30),
    )
    gemini = MagicMock()
    gemini.request_tool_turn = AsyncMock(return_value=GeminiToolTurn(
        text=None,
        calls=[GeminiFunctionCall("create_booking", {"slot_id": str(confirmation.slot_id)})],
        contents=[],
        model_content=MagicMock(),
    ))
    gemini.complete_tool_turn = AsyncMock()
    tools = MagicMock()
    tools.execute = AsyncMock(return_value=ToolResult(
        name="create_booking",
        status="CONFIRMATION_REQUIRED",
        data=confirmation.model_dump(mode="json"),
    ))
    response = await ChatOrchestrator(gemini, None, tools, settings()).reply(
        ChatRequest(message="Đặt slot này", use_rag=False), patient
    )
    assert response.booking_confirmation is not None
    gemini.complete_tool_turn.assert_not_awaited()


@pytest.mark.anyio
async def test_tool_timeout_is_not_reported_as_success() -> None:
    gemini = MagicMock()
    gemini.request_tool_turn = AsyncMock(return_value=GeminiToolTurn(
        text=None,
        calls=[GeminiFunctionCall("search_specialty", {"query": "tim"})],
        contents=[],
        model_content=MagicMock(),
    ))
    tools = MagicMock()

    async def slow(*_args):
        await asyncio.sleep(0.05)

    tools.execute = slow
    config = settings()
    config.tool_timeout_seconds = 0.01
    with pytest.raises(Exception) as caught:
        await ChatOrchestrator(gemini, None, tools, config).reply(
            ChatRequest(message="Tìm chuyên khoa", use_rag=False), actor("PATIENT")
        )
    assert getattr(caught.value, "code", None) == "tool_timeout"


def test_tool_layer_has_no_direct_orm_sql_or_medical_record_import() -> None:
    root = Path(__file__).resolve().parents[1] / "app" / "ai" / "tools"
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py")).lower()
    assert "from sqlalchemy" not in source
    assert "select(" not in source
    assert "session.execute" not in source
    assert "medical_record" not in source

