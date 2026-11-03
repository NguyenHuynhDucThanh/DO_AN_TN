"""Appointment persistence and locking."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.care import Appointment, DoctorSchedule, ScheduleSlot
from app.models.enums import AppointmentStatus


class AppointmentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _load_statement():
        return select(Appointment).options(
            selectinload(Appointment.schedule_slot)
            .selectinload(ScheduleSlot.schedule)
            .selectinload(DoctorSchedule.doctor)
        )

    def get(self, appointment_id: UUID, *, for_update: bool = False) -> Appointment | None:
        statement = self._load_statement().where(Appointment.id == appointment_id)
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def list_for_actor(self, actor_user_id: UUID, roles: frozenset[str]) -> list[Appointment]:
        statement = self._load_statement().order_by(Appointment.booked_at.desc())
        if roles.intersection({"STAFF", "ADMIN"}):
            return list(self.session.scalars(statement))
        if "DOCTOR" in roles:
            statement = (
                statement.join(Appointment.schedule_slot)
                .join(ScheduleSlot.schedule)
                .join(DoctorSchedule.doctor)
                .where(DoctorSchedule.doctor.has(user_id=actor_user_id))
            )
        else:
            statement = statement.where(Appointment.patient_id == actor_user_id)
        return list(self.session.scalars(statement))

    def lock_slot(self, slot_id: UUID) -> ScheduleSlot | None:
        return self.session.scalar(
            select(ScheduleSlot)
            .options(selectinload(ScheduleSlot.schedule).selectinload(DoctorSchedule.doctor))
            .where(ScheduleSlot.id == slot_id)
            .with_for_update()
        )

    def has_occupied_appointment(self, slot_id: UUID) -> bool:
        return self.session.scalar(
            select(Appointment.id).where(
                Appointment.schedule_slot_id == slot_id,
                Appointment.status.in_(
                    [AppointmentStatus.CONFIRMED, AppointmentStatus.COMPLETED, AppointmentStatus.NO_SHOW]
                ),
            )
        ) is not None

    def add(self, appointment: Appointment) -> Appointment:
        self.session.add(appointment)
        return appointment
