"""Basic post-visit medical record; deliberately excludes EMR/HIS scope."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class MedicalRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "medical_records"
    __table_args__ = (UniqueConstraint("appointment_id", name="uq_medical_records_appointment_id"),)

    appointment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("appointments.id", ondelete="RESTRICT"), nullable=False
    )
    symptoms: Mapped[str] = mapped_column(Text, nullable=False)
    clinical_notes: Mapped[str] = mapped_column(Text, nullable=False)
    doctor_conclusion: Mapped[str] = mapped_column(Text, nullable=False)
    follow_up_instructions: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    updated_by: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    appointment: Mapped["Appointment"] = relationship(back_populates="medical_record")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])
    updater: Mapped["User"] = relationship(foreign_keys=[updated_by])
