"""Handoff ticket contracts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import HandoffPriority, HandoffStatus


class HandoffCreate(BaseModel):
    reason: str = Field(min_length=2, max_length=5000)
    priority: HandoffPriority = HandoffPriority.NORMAL
    source: str = Field(default="USER", min_length=2, max_length=30)


class HandoffUpdate(BaseModel):
    assigned_to: UUID | None = None
    status: HandoffStatus


class HandoffRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    requester_id: UUID
    assigned_to: UUID | None
    source: str
    reason: str
    priority: HandoffPriority
    status: HandoffStatus
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime
