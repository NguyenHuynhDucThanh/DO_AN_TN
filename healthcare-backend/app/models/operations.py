"""Human handoff and metadata-only audit trail models."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import HandoffPriority, HandoffStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


def enum_type(enum_class: type, name: str, length: int = 32) -> Enum:
    return Enum(enum_class, name=name, native_enum=False, create_constraint=True, length=length)


class HandoffRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "handoff_requests"

    requester_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assigned_to: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="CHATBOT", server_default="CHATBOT")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[HandoffPriority] = mapped_column(
        enum_type(HandoffPriority, "handoff_priority", 16), nullable=False,
        default=HandoffPriority.NORMAL, server_default=HandoffPriority.NORMAL.value,
    )
    status: Mapped[HandoffStatus] = mapped_column(
        enum_type(HandoffStatus, "handoff_status", 16), nullable=False,
        default=HandoffStatus.PENDING, server_default=HandoffStatus.PENDING.value,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_occurred_at", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    request_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    audit_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict, server_default="{}")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
