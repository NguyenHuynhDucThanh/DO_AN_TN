"""Phase 11 Voice input and Handoff realtime isolation tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
import pytest

from app.auth.context import ActorContext
from app.core.config import Settings
from app.core.errors import BadRequestError, UnauthorizedError
from app.handoffs.realtime import HandoffConnectionManager, handoff_event_payload
from app.models.enums import HandoffPriority, HandoffStatus
from app.voice.schemas import TranscriptionResponse
from app.voice.service import TranscriptionService


def actor(*roles: str) -> ActorContext:
    return ActorContext(uuid4(), frozenset(roles))


def settings(**overrides) -> Settings:
    values = {
        "database_url": "postgresql+psycopg://unit:unit@localhost/unit",
        "jwt_secret": "phase-11-unit-test-secret-with-32-characters",
        "stt_max_file_bytes": 100_000,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


class FakeTranscriber:
    def __init__(self, response: TranscriptionResponse | Exception) -> None:
        self.response = response
        self.path: Path | None = None

    def transcribe(self, path: Path) -> TranscriptionResponse:
        assert path.exists()
        self.path = path
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


@pytest.fixture
def voice_client():
    from app.auth.dependencies import get_current_actor
    from app.core.config import get_settings
    from app.main import create_app
    from app.voice.router import get_transcription_service

    application = create_app()
    fake = FakeTranscriber(TranscriptionResponse(transcript="Tôi cần tìm bác sĩ tim mạch"))
    application.dependency_overrides[get_current_actor] = lambda: actor("PATIENT")
    application.dependency_overrides[get_settings] = lambda: settings()
    application.dependency_overrides[get_transcription_service] = lambda: fake
    with TestClient(application) as client:
        yield client, fake, application


def test_voice_upload_returns_vietnamese_transcript_and_cleans_temp_file(voice_client) -> None:
    client, fake, _application = voice_client
    response = client.post(
        "/api/v1/voice/transcriptions",
        files={"audio": ("ignored-name.webm", b"synthetic-audio", "audio/webm")},
    )
    assert response.status_code == 200
    assert response.json()["transcript"] == "Tôi cần tìm bác sĩ tim mạch"
    assert fake.path is not None and not fake.path.exists()


@pytest.mark.parametrize(
    ("payload", "mime", "expected_code"),
    [
        (b"", "audio/webm", "empty_audio"),
        (b"content", "application/octet-stream", "unsupported_audio_format"),
        (b"x" * 100_001, "audio/webm", "audio_too_large"),
    ],
    ids=["empty", "unsupported", "oversized"],
)
def test_voice_upload_validation(voice_client, payload: bytes, mime: str, expected_code: str) -> None:
    client, _fake, _application = voice_client
    response = client.post(
        "/api/v1/voice/transcriptions",
        files={"audio": ("untrusted.exe", payload, mime)},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == expected_code


def test_voice_stt_failure_cleans_temp_file(voice_client) -> None:
    client, fake, application = voice_client
    from app.voice.router import get_transcription_service

    failed = FakeTranscriber(BadRequestError("No speech", "no_speech_detected"))
    application.dependency_overrides[get_transcription_service] = lambda: failed
    response = client.post(
        "/api/v1/voice/transcriptions",
        files={"audio": ("voice.webm", b"synthetic-audio", "audio/webm")},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "no_speech_detected"
    assert failed.path is not None and not failed.path.exists()
    assert fake.path is None


def test_transcription_service_uses_vietnamese_and_rejects_no_speech() -> None:
    segment = SimpleNamespace(text="  Xin chào  ")
    info = SimpleNamespace(language="vi", duration=1.25)
    model = MagicMock()
    model.transcribe.return_value = ([segment], info)
    result = TranscriptionService(settings(), model=model).transcribe(Path("synthetic.webm"))
    assert result.transcript == "Xin chào"
    assert result.language == "vi"
    assert model.transcribe.call_args.kwargs["language"] == "vi"
    assert model.transcribe.call_args.kwargs["task"] == "transcribe"
    assert model.transcribe.call_args.kwargs["temperature"] == 0.0
    assert "tiếng Việt" in model.transcribe.call_args.kwargs["initial_prompt"]

    model.transcribe.return_value = ([], info)
    with pytest.raises(BadRequestError) as exc_info:
        TranscriptionService(settings(), model=model).transcribe(Path("silent.webm"))
    assert exc_info.value.code == "no_speech_detected"


class FakeSocket:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.events: list[dict] = []

    async def accept(self) -> None: pass

    async def send_json(self, event: dict) -> None:
        if self.fail:
            raise RuntimeError("socket unavailable")
        self.events.append(event)


@pytest.mark.anyio
async def test_handoff_realtime_metadata_and_failure_isolation() -> None:
    manager = HandoffConnectionManager()
    staff_id = uuid4()
    healthy = FakeSocket()
    broken = FakeSocket(fail=True)
    await manager.connect(staff_id, healthy)  # type: ignore[arg-type]
    await manager.connect(uuid4(), broken)  # type: ignore[arg-type]
    request = SimpleNamespace(
        id=uuid4(), requester_id=uuid4(), assigned_to=None, source="RISK_ALERT",
        reason="clinical text must not be pushed", priority=HandoffPriority.URGENT,
        status=HandoffStatus.PENDING, created_at=None, updated_at=None,
    )
    event = handoff_event_payload("handoff.created", request)
    assert "reason" not in event["handoff"]
    assert "medical" not in str(event).lower()
    await manager.publish(event)
    assert healthy.events == [event]
    assert manager.connection_count == 1


def test_handoff_websocket_authentication_and_role(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.handoffs.router as handoff_router
    from app.core.database import get_db
    from app.main import create_app

    application = create_app()
    application.dependency_overrides[get_db] = lambda: MagicMock()
    client = TestClient(application)

    monkeypatch.setattr(handoff_router, "get_websocket_actor", lambda _ws, _db: actor("STAFF"))
    with client.websocket_connect(
        "/api/v1/handoffs/ws", headers={"origin": "http://localhost:5173"}
    ) as websocket:
        assert websocket.receive_json() == {"type": "handoff.connected"}

    monkeypatch.setattr(
        handoff_router,
        "get_websocket_actor",
        lambda _ws, _db: (_ for _ in ()).throw(UnauthorizedError()),
    )
    with pytest.raises(WebSocketDisconnect) as unauthorized:
        with client.websocket_connect("/api/v1/handoffs/ws"):
            pass
    assert unauthorized.value.code == 4401

    monkeypatch.setattr(handoff_router, "get_websocket_actor", lambda _ws, _db: actor("PATIENT"))
    with pytest.raises(WebSocketDisconnect) as forbidden:
        with client.websocket_connect("/api/v1/handoffs/ws"):
            pass
    assert forbidden.value.code == 4403
