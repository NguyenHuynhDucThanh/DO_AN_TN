"""Strict, identity-free argument contracts for Gemini function calls."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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
    doctor_id: UUID
    date: date


class CreateBookingArgs(ToolArguments):
    slot_id: UUID


class HandoffToStaffArgs(ToolArguments):
    reason: str = Field(min_length=2, max_length=5000)


class ConfirmBookingRequest(ToolArguments):
    confirmation_token: str = Field(min_length=20, max_length=2000)

