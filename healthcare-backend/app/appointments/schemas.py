"""Appointment API contracts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AppointmentStatus


class AppointmentCreate(BaseModel):
    schedule_slot_id: UUID


class AppointmentCancel(BaseModel):
    reason: str = Field(min_length=2, max_length=500)


class AppointmentOutcome(BaseModel):
    status: AppointmentStatus


class AppointmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    patient_id: UUID
    schedule_slot_id: UUID
    status: AppointmentStatus
    booked_at: datetime
    cancelled_at: datetime | None
    cancelled_by: UUID | None
    cancellation_reason: str | None
    completed_at: datetime | None
    no_show_at: datetime | None
    created_at: datetime
    updated_at: datetime
