"""Schedule and slot API contracts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ScheduleStatus, SlotStatus


def require_timezone(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("A timezone offset is required")
    return value


class ScheduleCreate(BaseModel):
    doctor_id: UUID
    start_at: datetime
    end_at: datetime
    slot_duration_minutes: int = Field(ge=5, le=480)

    _start_timezone = field_validator("start_at")(require_timezone)
    _end_timezone = field_validator("end_at")(require_timezone)


class ScheduleUpdate(BaseModel):
    start_at: datetime | None = None
    end_at: datetime | None = None
    slot_duration_minutes: int | None = Field(default=None, ge=5, le=480)
    status: ScheduleStatus | None = None

    _start_timezone = field_validator("start_at")(lambda value: require_timezone(value) if value else value)
    _end_timezone = field_validator("end_at")(lambda value: require_timezone(value) if value else value)


class ScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    doctor_id: UUID
    start_at: datetime
    end_at: datetime
    slot_duration_minutes: int
    status: ScheduleStatus
    created_at: datetime
    updated_at: datetime


class SlotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    schedule_id: UUID
    start_at: datetime
    end_at: datetime
    status: SlotStatus
    created_at: datetime
    updated_at: datetime


class SlotStatusUpdate(BaseModel):
    blocked: bool
