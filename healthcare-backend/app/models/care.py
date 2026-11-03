"""Medical master data and appointment scheduling models."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import AppointmentStatus, ScheduleStatus, SlotStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


def enum_type(enum_class: type, name: str, length: int = 32) -> Enum:
    return Enum(enum_class, name=name, native_enum=False, create_constraint=True, length=length)


class Specialty(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "specialties"

    code: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

    doctors: Mapped[list[Doctor]] = relationship(back_populates="specialty")


class Doctor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "doctors"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    specialty_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("specialties.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    license_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    biography: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

    user: Mapped["User"] = relationship()
    specialty: Mapped[Specialty] = relationship(back_populates="doctors")
    schedules: Mapped[list[DoctorSchedule]] = relationship(back_populates="doctor")


class DoctorSchedule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "doctor_schedules"
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="valid_time_range"),
        CheckConstraint("slot_duration_minutes BETWEEN 5 AND 480", name="valid_slot_duration"),
        UniqueConstraint("doctor_id", "start_at", "end_at", name="uq_doctor_schedules_doctor_range"),
    )

    doctor_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("doctors.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    slot_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ScheduleStatus] = mapped_column(
        enum_type(ScheduleStatus, "schedule_status", 16), nullable=False,
        default=ScheduleStatus.ACTIVE, server_default=ScheduleStatus.ACTIVE.value,
    )

    doctor: Mapped[Doctor] = relationship(back_populates="schedules")
    slots: Mapped[list[ScheduleSlot]] = relationship(
        back_populates="schedule", cascade="all, delete-orphan", order_by="ScheduleSlot.start_at"
    )


class ScheduleSlot(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "schedule_slots"
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="valid_time_range"),
        UniqueConstraint("schedule_id", "start_at", name="uq_schedule_slots_schedule_start"),
    )

    schedule_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("doctor_schedules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[SlotStatus] = mapped_column(
        enum_type(SlotStatus, "slot_status", 16), nullable=False,
        default=SlotStatus.AVAILABLE, server_default=SlotStatus.AVAILABLE.value,
    )

    schedule: Mapped[DoctorSchedule] = relationship(back_populates="slots")
    appointments: Mapped[list[Appointment]] = relationship(back_populates="schedule_slot")


class Appointment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "appointments"
    __table_args__ = (
        Index(
            "uq_appointments_occupied_slot",
            "schedule_slot_id",
            unique=True,
            postgresql_where=text("status IN ('CONFIRMED', 'COMPLETED', 'NO_SHOW')"),
        ),
        CheckConstraint(
            "(status <> 'CANCELLED') OR cancelled_at IS NOT NULL",
            name="cancelled_has_timestamp",
        ),
        CheckConstraint(
            "(status <> 'COMPLETED') OR completed_at IS NOT NULL",
            name="completed_has_timestamp",
        ),
        CheckConstraint(
            "(status <> 'NO_SHOW') OR no_show_at IS NOT NULL",
            name="no_show_has_timestamp",
        ),
    )

    patient_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    schedule_slot_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("schedule_slots.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[AppointmentStatus] = mapped_column(
        enum_type(AppointmentStatus, "appointment_status", 16), nullable=False,
        default=AppointmentStatus.CONFIRMED, server_default=AppointmentStatus.CONFIRMED.value,
    )
    booked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    cancellation_reason: Mapped[str | None] = mapped_column(String(500))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    no_show_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    patient: Mapped["User"] = relationship(foreign_keys=[patient_id])
    schedule_slot: Mapped[ScheduleSlot] = relationship(back_populates="appointments")
    medical_record: Mapped["MedicalRecord | None"] = relationship(back_populates="appointment", uselist=False)
