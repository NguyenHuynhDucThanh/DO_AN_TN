"""Phase 7 chatbot tests never call the real Gemini API."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from google.genai import errors
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.ai.chat_service import ChatService
from app.ai.errors import ChatbotInvalidResponseError, ChatbotUnavailableError
from app.ai.gemini_client import GeminiClient, SAFETY_INSTRUCTION
from app.ai.router import get_chat_service
from app.ai.schemas import ChatHistoryItem, ChatRequest
from app.auth.context import ActorContext
from app.auth.dependencies import get_current_actor
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.main import create_app


class FakeAsyncClient:
    def __init__(self, result: Any = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[dict[str, Any]] = []
        self.models = self

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def generate_content(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.result

    async def get(self, **_kwargs: Any) -> Any:
        if self.error is not None:
            raise self.error
        return SimpleNamespace(name="configured-model")


class FakeSdkClient:
    def __init__(self, async_client: FakeAsyncClient) -> None:
        self.aio = async_client


def configured_settings(**overrides: Any) -> Settings:
    values = {
        "database_url": "postgresql+psycopg://unit:unit@localhost/unit",
        "gemini_api_key": "synthetic-key-never-sent",
        "gemini_model": "configured-test-model",
        "gemini_timeout_seconds": 5,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def client_with(fake: FakeAsyncClient, **settings: Any) -> GeminiClient:
    return GeminiClient(
        configured_settings(**settings),
        client_factory=lambda **_kwargs: FakeSdkClient(fake),
    )


@pytest.mark.anyio
async def test_success_uses_safety_instruction_and_text_only_context() -> None:
    fake = FakeAsyncClient(SimpleNamespace(text="  Câu trả lời an toàn.  ", function_calls=None))
    client = client_with(fake)
    answer = await client.generate_reply(
        "Tôi nên chuẩn bị gì trước khi khám?",
        [ChatHistoryItem(role="assistant", content="Bạn muốn hỏi điều gì?")],
    )

    assert answer == "Câu trả lời an toàn."
    call = fake.calls[0]
    assert call["model"] == "configured-test-model"
    assert call["config"].system_instruction == SAFETY_INSTRUCTION
    assert "không khẳng định chẩn đoán" in SAFETY_INSTRUCTION.lower()
    assert "không kê đơn" in SAFETY_INSTRUCTION.lower()
    assert call["config"].tools is None
    assert call["config"].automatic_function_calling.disable is True
    assert [content.role for content in call["contents"]] == ["model", "user"]
    assert call["contents"][-1].parts[0].text == "Tôi nên chuẩn bị gì trước khi khám?"


@pytest.mark.parametrize(
    "payload",
    [
        {"message": ""},
        {"message": "   "},
        {"message": "x" * 4001},
        {"message": "hợp lệ", "unknown": "field"},
        {"message": "hợp lệ", "history": [{"role": "system", "content": "bad"}]},
    ],
)
def test_rejects_empty_too_long_and_malformed_input(payload: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        ChatRequest.model_validate(payload)


@pytest.mark.anyio
async def test_missing_configuration_has_safe_fallback() -> None:
    client = GeminiClient(configured_settings(gemini_api_key=None, gemini_model=None))
    with pytest.raises(ChatbotUnavailableError) as error:
        await client.generate_reply("Xin chào", [])
    assert error.value.code == "chatbot_not_configured"
    assert "key" not in error.value.detail.lower()


@pytest.mark.anyio
async def test_timeout_and_network_failure_are_controlled() -> None:
    with pytest.raises(ChatbotUnavailableError) as timeout:
        await client_with(FakeAsyncClient(error=asyncio.TimeoutError())).generate_reply("Xin chào", [])
    assert timeout.value.code == "chatbot_timeout"

    request = httpx.Request("POST", "https://generativelanguage.googleapis.com")
    with pytest.raises(ChatbotUnavailableError) as network:
        await client_with(
            FakeAsyncClient(error=httpx.ConnectError("private upstream detail", request=request))
        ).generate_reply("Xin chào", [])
    assert network.value.code == "chatbot_unavailable"
    assert "private upstream detail" not in network.value.detail


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("status", "expected_code"),
    [
        (429, "chatbot_rate_limited"),
        (401, "chatbot_authentication_failed"),
        (403, "chatbot_authentication_failed"),
        (404, "chatbot_model_unavailable"),
        (400, "chatbot_configuration_error"),
        (500, "chatbot_unavailable"),
    ],
)
async def test_provider_errors_are_mapped_without_raw_details(
    status: int, expected_code: str
) -> None:
    provider_error = errors.ClientError(
        status,
        {"error": {"message": "secret provider response"}},
    ) if status < 500 else errors.ServerError(
        status,
        {"error": {"message": "secret provider response"}},
    )
    with pytest.raises(ChatbotUnavailableError) as caught:
        await client_with(FakeAsyncClient(error=provider_error)).generate_reply("Xin chào", [])
    assert caught.value.code == expected_code
    assert "secret provider response" not in caught.value.detail


@pytest.mark.anyio
@pytest.mark.parametrize(
    "response",
    [
        SimpleNamespace(text="", function_calls=None),
        SimpleNamespace(text=None, function_calls=None),
        SimpleNamespace(text="answer", function_calls=[{"name": "forbidden_tool"}]),
    ],
)
async def test_empty_invalid_or_function_call_response_is_rejected(response: Any) -> None:
    with pytest.raises(ChatbotInvalidResponseError):
        await client_with(FakeAsyncClient(result=response)).generate_reply("Xin chào", [])


@pytest.mark.anyio
async def test_chat_service_returns_stable_contract() -> None:
    client = MagicMock()
    client.generate_reply = AsyncMock(return_value="Nội dung trả lời")
    response = await ChatService(client).reply(ChatRequest(message="Câu hỏi"))
    assert response.model_dump() == {
        "answer": "Nội dung trả lời",
        "sources": [],
        "tool_results": [],
        "booking_confirmation": None,
        "risk_alert": None,
    }


@pytest.mark.anyio
async def test_chat_endpoint_success_and_validation() -> None:
    get_settings.cache_clear()
    app = create_app()
    service = MagicMock()
    service.reply = AsyncMock(return_value=SimpleNamespace(answer="Phản hồi an toàn"))
    app.dependency_overrides[get_current_actor] = lambda: ActorContext(
        user_id=uuid4(), roles=frozenset({"PATIENT"})
    )
    app.dependency_overrides[get_chat_service] = lambda: service

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        success = await client.post(
            "/api/v1/chat/messages", json={"message": "Xin chào", "history": []}
        )
        empty = await client.post("/api/v1/chat/messages", json={"message": "   "})
        malformed = await client.post(
            "/api/v1/chat/messages", json={"message": "Xin chào", "unknown": True}
        )

    assert success.status_code == 200
    assert success.json() == {
        "answer": "Phản hồi an toàn",
        "sources": [],
        "tool_results": [],
        "booking_confirmation": None,
        "risk_alert": None,
    }
    assert empty.status_code == malformed.status_code == 422
    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.mark.anyio
async def test_chat_failure_does_not_affect_business_health(health_session: MagicMock) -> None:
    get_settings.cache_clear()
    app = create_app()
    failing_service = MagicMock()
    failing_service.reply = AsyncMock(
        side_effect=ChatbotUnavailableError(code="chatbot_model_unavailable")
    )
    app.dependency_overrides[get_current_actor] = lambda: ActorContext(
        user_id=uuid4(), roles=frozenset({"PATIENT"})
    )
    app.dependency_overrides[get_chat_service] = lambda: failing_service
    app.dependency_overrides[get_db] = lambda: health_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        chat = await client.post("/api/v1/chat/messages", json={"message": "Xin chào"})
        health = await client.get("/api/v1/health")

    assert chat.status_code == 503
    assert chat.json() == {
        "error": {
            "code": "chatbot_model_unavailable",
            "detail": "Chatbot is temporarily unavailable. Please try again later.",
        }
    }
    assert health.status_code == 200
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_ai_module_has_no_tool_or_medical_record_dependency() -> None:
    ai_root = Path(__file__).resolve().parents[1] / "app" / "ai"
    source = "\n".join(path.read_text(encoding="utf-8") for path in ai_root.glob("*.py")).lower()
    forbidden_imports = (
        "app.appointments",
        "app.schedules",
        "app.handoffs",
        "app.medical_records",
        "app.models.medical_record",
    )
    assert all(name not in source for name in forbidden_imports)
    assert "tools=none" in source
