"""Stable chatbot, tool result, and explicit booking confirmation contracts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.rag.schemas import RagSource

MAX_CHAT_MESSAGE_CHARS = 4000
MAX_CHAT_HISTORY_ITEMS = 10


class ChatHistoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=MAX_CHAT_MESSAGE_CHARS)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message content must not be empty")
        return value


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=MAX_CHAT_MESSAGE_CHARS)
    history: list[ChatHistoryItem] = Field(default_factory=list, max_length=MAX_CHAT_HISTORY_ITEMS)
    use_rag: bool = True

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message must not be empty")
        return value


class RiskHandoff(BaseModel):
    status: Literal["PENDING", "FAILED"]
    handoff_id: UUID | None = None
    message: str


class RiskAlert(BaseModel):
    level: Literal["URGENT"] = "URGENT"
    title: str
    message: str
    recommended_actions: list[str]
    rule_codes: list[str]
    handoff: RiskHandoff


class ChatResponse(BaseModel):
    answer: str
    sources: list[RagSource] = Field(default_factory=list)
    tool_results: list["ToolResult"] = Field(default_factory=list)
    booking_confirmation: "BookingConfirmation | None" = None
    risk_alert: RiskAlert | None = None


class ToolResult(BaseModel):
    name: str
    status: Literal["SUCCESS", "CONFIRMATION_REQUIRED"]
    data: dict[str, object] = Field(default_factory=dict)


class BookingConfirmation(BaseModel):
    status: Literal["CONFIRMATION_REQUIRED"] = "CONFIRMATION_REQUIRED"
    confirmation_token: str
    slot_id: UUID
    doctor_id: UUID
    doctor_name: str
    specialty_id: UUID
    specialty_name: str
    start_at: datetime
    end_at: datetime


class BookingConfirmationResponse(BaseModel):
    status: Literal["BOOKED"] = "BOOKED"
    appointment_id: UUID
    slot_id: UUID
