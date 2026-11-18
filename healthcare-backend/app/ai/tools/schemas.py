"""Strict, identity-free argument contracts for Gemini function calls."""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ToolArguments(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SearchSpecialtyArgs(ToolArguments):
    query: str = Field(min_length=1, max_length=120)


class DoctorFilters(ToolArguments):
    active_only: bool = True


class ListDoctorsArgs(ToolArguments):
    specialty_id: UUID
    filters: DoctorFilters = Field(default_factory=DoctorFilters)


class AvailableSlotsArgs(ToolArguments):
    doctor_id: UUID | None = None
    specialty_id: UUID | None = None
    date: date
    period: Literal["ALL", "MORNING", "AFTERNOON", "EVENING"] = "ALL"

    @model_validator(mode="after")
    def require_doctor_or_specialty(self) -> "AvailableSlotsArgs":
        if self.doctor_id is None and self.specialty_id is None:
            raise ValueError("doctor_id or specialty_id is required")
        return self


class CreateBookingArgs(ToolArguments):
    slot_id: UUID


class HandoffToStaffArgs(ToolArguments):
    reason: str = Field(min_length=2, max_length=5000)


class ConfirmBookingRequest(ToolArguments):
    confirmation_token: str = Field(min_length=20, max_length=2000)

