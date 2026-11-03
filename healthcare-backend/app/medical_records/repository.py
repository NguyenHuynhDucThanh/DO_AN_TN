"""MedicalRecord persistence with appointment ownership context."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.care import Appointment, DoctorSchedule, ScheduleSlot
from app.models.medical_record import MedicalRecord


class MedicalRecordRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _record_statement():
        return select(MedicalRecord).options(
            selectinload(MedicalRecord.appointment)
            .selectinload(Appointment.schedule_slot)
            .selectinload(ScheduleSlot.schedule)
            .selectinload(DoctorSchedule.doctor)
        )

    @staticmethod
    def _appointment_statement():
        return select(Appointment).options(
            selectinload(Appointment.schedule_slot)
            .selectinload(ScheduleSlot.schedule)
            .selectinload(DoctorSchedule.doctor),
            selectinload(Appointment.medical_record),
        )

    def get(self, record_id: UUID, *, for_update: bool = False) -> MedicalRecord | None:
        statement = self._record_statement().where(MedicalRecord.id == record_id)
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def get_by_appointment(self, appointment_id: UUID) -> MedicalRecord | None:
        return self.session.scalar(
            self._record_statement().where(MedicalRecord.appointment_id == appointment_id)
        )

    def get_appointment(self, appointment_id: UUID, *, for_update: bool = False) -> Appointment | None:
        statement = self._appointment_statement().where(Appointment.id == appointment_id)
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def list_patient_history(self, patient_id: UUID) -> list[MedicalRecord]:
        return list(
            self.session.scalars(
                self._record_statement()
                .join(MedicalRecord.appointment)
                .where(Appointment.patient_id == patient_id)
                .order_by(Appointment.completed_at.desc(), MedicalRecord.created_at.desc())
            )
        )

    def add(self, record: MedicalRecord) -> MedicalRecord:
        self.session.add(record)
        return record
