"""Lazy faster-whisper transcription with no durable audio storage."""

from __future__ import annotations

import gc
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.core.config import Settings, get_settings
from app.core.errors import BadRequestError
from app.core.model_runtime import HEAVY_MODEL_LOCK
from app.documents.embeddings import get_embedding_service
from app.voice.schemas import TranscriptionResponse


VIETNAMESE_TRANSCRIPTION_PROMPT = (
    "Đây là lời nói tiếng Việt của người dùng về sức khỏe. "
    "Hãy chép lại nguyên văn bằng tiếng Việt có dấu, không dịch sang ngôn ngữ khác."
)


class WhisperModelLike(Protocol):
    def transcribe(self, audio: str, **kwargs): ...


@lru_cache(maxsize=2)
def _load_model(model_name: str, device: str, compute_type: str) -> WhisperModelLike:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:  # pragma: no cover - installation/configuration guard
        raise RuntimeError("faster-whisper is not installed") from exc
    return WhisperModel(model_name, device=device, compute_type=compute_type)


class TranscriptionService:
    def __init__(
        self,
        settings: Settings | None = None,
        model: WhisperModelLike | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._model = model

    def transcribe(self, audio_path: Path) -> TranscriptionResponse:
        owns_model = self._model is None
        model = self._model
        with HEAVY_MODEL_LOCK:
            try:
                if owns_model:
                    get_embedding_service().release_model()
                    gc.collect()
                    model = _load_model(
                        self.settings.stt_model,
                        self.settings.stt_device,
                        self.settings.stt_compute_type,
                    )
                assert model is not None
                segments, info = model.transcribe(
                    str(audio_path),
                    language="vi",
                    task="transcribe",
                    beam_size=5,
                    temperature=0.0,
                    vad_filter=True,
                    condition_on_previous_text=False,
                    initial_prompt=VIETNAMESE_TRANSCRIPTION_PROMPT,
                )
                transcript = " ".join(
                    segment.text.strip() for segment in segments if segment.text.strip()
                ).strip()
            except Exception as exc:
                raise BadRequestError(
                    "Audio could not be decoded or transcribed.", "invalid_or_corrupt_audio"
                ) from exc
            finally:
                if owns_model:
                    _load_model.cache_clear()
                    model = None
                    gc.collect()
        if not transcript:
            raise BadRequestError("No usable speech was detected.", "no_speech_detected")
        duration = getattr(info, "duration", None)
        return TranscriptionResponse(
            transcript=transcript,
            language=getattr(info, "language", None) or "vi",
            duration_seconds=float(duration) if duration is not None else None,
        )
