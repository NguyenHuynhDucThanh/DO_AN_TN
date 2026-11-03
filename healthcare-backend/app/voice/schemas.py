"""Voice transcription API contracts."""

from pydantic import BaseModel


class TranscriptionResponse(BaseModel):
    transcript: str
    language: str = "vi"
    duration_seconds: float | None = None
