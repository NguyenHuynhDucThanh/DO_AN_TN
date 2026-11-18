"""Appointment API contracts."""

from datetime import datetime
from uuid import UUID

from pydantic import AliasPath, BaseModel, ConfigDict, Field, computed_field

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
    slot_start_at: datetime = Field(
        validation_alias=AliasPath("schedule_slot", "start_at")
    )
    slot_end_at: datetime = Field(
        validation_alias=AliasPath("schedule_slot", "end_at")
    )
    doctor_id: UUID = Field(
        validation_alias=AliasPath("schedule_slot", "schedule", "doctor", "id")
    )
    doctor_name: str = Field(
        validation_alias=AliasPath(
            "schedule_slot", "schedule", "doctor", "user", "full_name"
        )
    )
    specialty_id: UUID = Field(
        validation_alias=AliasPath(
            "schedule_slot", "schedule", "doctor", "specialty", "id"
        )
    )
    specialty_name: str = Field(
        validation_alias=AliasPath(
            "schedule_slot", "schedule", "doctor", "specialty", "name"
        )
    )
    patient_name: str = Field(validation_alias=AliasPath("patient", "full_name"))

    @computed_field(return_type=str)
    @property
    def reference_code(self) -> str:
        """Stable user-facing reference; UUID remains the authoritative key."""
        return f"LH-{self.id.hex[:8].upper()}"
