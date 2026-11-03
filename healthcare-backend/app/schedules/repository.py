"""Schedule and slot persistence queries."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.models.care import Doctor, DoctorSchedule, ScheduleSlot
from app.models.enums import ScheduleStatus, SlotStatus


class ScheduleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def lock_doctor(self, doctor_id: UUID) -> None:
        self.session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:doctor_id, 0))"),
            {"doctor_id": str(doctor_id)},
        )

    def list(self, doctor_id: UUID | None = None) -> list[DoctorSchedule]:
        statement = select(DoctorSchedule).order_by(DoctorSchedule.start_at)
        if doctor_id is not None:
            statement = statement.where(DoctorSchedule.doctor_id == doctor_id)
        return list(self.session.scalars(statement))

    def get(self, schedule_id: UUID, *, for_update: bool = False) -> DoctorSchedule | None:
        statement = (
            select(DoctorSchedule)
            .options(selectinload(DoctorSchedule.doctor))
            .where(DoctorSchedule.id == schedule_id)
        )
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def get_doctor(self, doctor_id: UUID) -> Doctor | None:
        return self.session.get(Doctor, doctor_id)

    def has_overlap(
        self,
        doctor_id: UUID,
        start_at: datetime,
        end_at: datetime,
        exclude_schedule_id: UUID | None = None,
    ) -> bool:
        statement = select(DoctorSchedule.id).where(
            DoctorSchedule.doctor_id == doctor_id,
            DoctorSchedule.status == ScheduleStatus.ACTIVE,
            DoctorSchedule.start_at < end_at,
            DoctorSchedule.end_at > start_at,
        )
        if exclude_schedule_id is not None:
            statement = statement.where(DoctorSchedule.id != exclude_schedule_id)
        return self.session.scalar(statement.limit(1)) is not None

    def add(self, schedule: DoctorSchedule) -> DoctorSchedule:
        self.session.add(schedule)
        return schedule

    def list_slots(self, schedule_id: UUID) -> list[ScheduleSlot]:
        return list(
            self.session.scalars(
                select(ScheduleSlot)
                .where(ScheduleSlot.schedule_id == schedule_id)
                .order_by(ScheduleSlot.start_at)
            )
        )

    def get_slot(self, slot_id: UUID, *, for_update: bool = False) -> ScheduleSlot | None:
        statement = (
            select(ScheduleSlot)
            .options(
                selectinload(ScheduleSlot.schedule)
                .selectinload(DoctorSchedule.doctor)
                .selectinload(Doctor.user),
                selectinload(ScheduleSlot.schedule)
                .selectinload(DoctorSchedule.doctor)
                .selectinload(Doctor.specialty),
            )
            .where(ScheduleSlot.id == slot_id)
        )
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def available_slots(
        self,
        from_at: datetime,
        to_at: datetime,
        doctor_id: UUID | None = None,
        specialty_id: UUID | None = None,
    ) -> list[ScheduleSlot]:
        statement = (
            select(ScheduleSlot)
            .join(ScheduleSlot.schedule)
            .join(DoctorSchedule.doctor)
            .options(
                selectinload(ScheduleSlot.schedule)
                .selectinload(DoctorSchedule.doctor)
                .selectinload(Doctor.user),
                selectinload(ScheduleSlot.schedule)
                .selectinload(DoctorSchedule.doctor)
                .selectinload(Doctor.specialty),
            )
            .where(
                ScheduleSlot.status == SlotStatus.AVAILABLE,
                DoctorSchedule.status == ScheduleStatus.ACTIVE,
                ScheduleSlot.start_at >= from_at,
                ScheduleSlot.start_at < to_at,
            )
            .order_by(ScheduleSlot.start_at)
        )
        if doctor_id is not None:
            statement = statement.where(DoctorSchedule.doctor_id == doctor_id)
        if specialty_id is not None:
            statement = statement.where(Doctor.specialty_id == specialty_id)
        return list(self.session.scalars(statement))
