"""MedicalRecord ownership, lifecycle, privacy, and audit rules."""

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.context import ActorContext
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.medical_records.repository import MedicalRecordRepository
from app.medical_records.schemas import MedicalRecordCreate, MedicalRecordUpdate
from app.models.care import Appointment
from app.models.enums import AppointmentStatus
from app.models.medical_record import MedicalRecord
from app.models.operations import AuditLog


class MedicalRecordService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = MedicalRecordRepository(session)

    @staticmethod
    def _doctor_user_id(appointment: Appointment) -> UUID:
        return appointment.schedule_slot.schedule.doctor.user_id

    def _authorize_read(self, record: MedicalRecord, actor: ActorContext) -> None:
        appointment = record.appointment
        if actor.has_any_role("PATIENT") and appointment.patient_id == actor.user_id:
            return
        if actor.has_any_role("DOCTOR") and self._doctor_user_id(appointment) == actor.user_id:
            return
        # STAFF/ADMIN deliberately receive no implicit clinical-read privilege.
        raise ForbiddenError("Clinical record access is restricted to its patient and assigned doctor.")

    def create_medical_record(
        self, data: MedicalRecordCreate, actor: ActorContext
    ) -> MedicalRecord:
        actor.require_any_role("DOCTOR")
        appointment = self.repository.get_appointment(data.appointment_id, for_update=True)
        if appointment is None:
            raise NotFoundError("Appointment was not found.", "appointment_not_found")
        if appointment.status != AppointmentStatus.COMPLETED:
            raise ConflictError(
                "A medical record can only be created for a completed appointment.",
                "appointment_not_completed",
            )
        if self._doctor_user_id(appointment) != actor.user_id:
            raise ForbiddenError("Only the assigned doctor can create this medical record.")
        if appointment.medical_record is not None:
            raise ConflictError(
                "This appointment already has a medical record.", "medical_record_exists"
            )
        payload = data.model_dump(exclude={"appointment_id"})
        record = MedicalRecord(
            appointment_id=appointment.id,
            created_by=actor.user_id,
            updated_by=actor.user_id,
            **{key: value.strip() for key, value in payload.items()},
        )
        self.repository.add(record)
        try:
            self.session.flush()
            self.session.add(
                AuditLog(
                    actor_user_id=actor.user_id,
                    action="MEDICAL_RECORD_CREATED",
                    entity_type="medical_record",
                    entity_id=record.id,
                    audit_metadata={"appointment_id": str(appointment.id)},
                )
            )
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError(
                "This appointment already has a medical record.", "medical_record_exists"
            ) from exc
        return self.get_medical_record(record.id, actor)

    def get_medical_record(self, record_id: UUID, actor: ActorContext) -> MedicalRecord:
        record = self.repository.get(record_id)
        if record is None:
            raise NotFoundError("Medical record was not found.", "medical_record_not_found")
        self._authorize_read(record, actor)
        return record

    def get_by_appointment(self, appointment_id: UUID, actor: ActorContext) -> MedicalRecord:
        record = self.repository.get_by_appointment(appointment_id)
        if record is None:
            raise NotFoundError("Medical record was not found.", "medical_record_not_found")
        self._authorize_read(record, actor)
        return record

    def update_medical_record(
        self, record_id: UUID, data: MedicalRecordUpdate, actor: ActorContext
    ) -> MedicalRecord:
        actor.require_any_role("DOCTOR")
        record = self.repository.get(record_id, for_update=True)
        if record is None:
            raise NotFoundError("Medical record was not found.", "medical_record_not_found")
        if self._doctor_user_id(record.appointment) != actor.user_id:
            raise ForbiddenError("Only the assigned doctor can update this medical record.")
        changes = data.model_dump(exclude_unset=True, exclude_none=True)
        for field, value in changes.items():
            setattr(record, field, value.strip())
        record.updated_by = actor.user_id
        self.session.add(
            AuditLog(
                actor_user_id=actor.user_id,
                action="MEDICAL_RECORD_UPDATED",
                entity_type="medical_record",
                entity_id=record.id,
                # Field names only: never symptoms, notes, conclusion, or instructions.
                audit_metadata={"changed_fields": sorted(changes)},
            )
        )
        self.session.commit()
        return self.get_medical_record(record.id, actor)

    def list_patient_medical_history(
        self, patient_id: UUID, actor: ActorContext
    ) -> list[MedicalRecord]:
        if not actor.has_any_role("PATIENT") or actor.user_id != patient_id:
            raise ForbiddenError("Patients can only view their own medical history.")
        return self.repository.list_patient_history(patient_id)
