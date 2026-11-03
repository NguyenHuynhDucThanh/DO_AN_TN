"""Authenticated audio upload endpoint for the Phase 11 input layer."""

from __future__ import annotations

import asyncio
from pathlib import Path
import tempfile
from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile

from app.auth.context import ActorContext
from app.auth.dependencies import get_current_actor
from app.core.config import Settings, get_settings
from app.core.errors import BadRequestError
from app.voice.schemas import TranscriptionResponse
from app.voice.service import TranscriptionService
from app.core.rate_limit import enforce_rate_limit

router = APIRouter(prefix="/voice", tags=["Voice"])

ALLOWED_AUDIO_TYPES = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
}


def get_transcription_service() -> TranscriptionService:
    return TranscriptionService()


async def _read_bounded(upload: UploadFile, limit: int) -> bytes:
    payload = await upload.read(limit + 1)
    if not payload:
        raise BadRequestError("Audio file is empty.", "empty_audio")
    if len(payload) > limit:
        raise BadRequestError("Audio file is too large.", "audio_too_large")
    return payload


@router.post("/transcriptions", response_model=TranscriptionResponse)
async def transcribe_audio(
    request: Request,
    actor: Annotated[ActorContext, Depends(get_current_actor)],
    service: Annotated[TranscriptionService, Depends(get_transcription_service)],
    audio: Annotated[UploadFile, File(description="Push-to-talk audio captured by MediaRecorder")],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TranscriptionResponse:
    enforce_rate_limit(
        request,
        scope="voice_transcription",
        identity=str(actor.user_id),
        limit=settings.voice_rate_limit,
        window_seconds=settings.common_rate_window_seconds,
        enabled=settings.rate_limit_enabled,
    )
    content_type = (audio.content_type or "").lower().split(";", 1)[0].strip()
    suffix = ALLOWED_AUDIO_TYPES.get(content_type)
    if suffix is None:
        raise BadRequestError("Audio format is not supported.", "unsupported_audio_format")
    payload = await _read_bounded(audio, settings.stt_max_file_bytes)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="healthcare-stt-", suffix=suffix, delete=False) as temporary:
            temporary.write(payload)
            temp_path = Path(temporary.name)
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(service.transcribe, temp_path),
                timeout=settings.stt_timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise BadRequestError("Speech transcription timed out.", "stt_timeout") from exc
    finally:
        await audio.close()
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
