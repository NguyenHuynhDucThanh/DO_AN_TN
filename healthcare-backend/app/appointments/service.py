"""Transactional booking and appointment lifecycle rules."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.appointments.repository import AppointmentRepository
from app.appointments.schemas import AppointmentCancel, AppointmentCreate, AppointmentOutcome
from app.auth.context import ActorContext
from app.core.errors import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.models.care import Appointment
from app.models.enums import AppointmentStatus, ScheduleStatus, SlotStatus
from app.models.operations import AuditLog


class AppointmentService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = AppointmentRepository(session)

    @staticmethod
    def _doctor_user_id(appointment: Appointment) -> UUID:
        return appointment.schedule_slot.schedule.doctor.user_id

    def _authorize_read(self, appointment: Appointment, actor: ActorContext) -> None:
        if actor.has_any_role("STAFF", "ADMIN"):
            return
        if appointment.patient_id == actor.user_id:
            return
        if actor.has_any_role("DOCTOR") and self._doctor_user_id(appointment) == actor.user_id:
            return
        raise ForbiddenError()

    def list(self, actor: ActorContext) -> list[Appointment]:
        return self.repository.list_for_actor(actor.user_id, actor.roles)

    def get(self, appointment_id: UUID, actor: ActorContext) -> Appointment:
        appointment = self.repository.get(appointment_id)
        if appointment is None:
            raise NotFoundError("Appointment was not found.", "appointment_not_found")
        self._authorize_read(appointment, actor)
        return appointment

    def create(self, data: AppointmentCreate, actor: ActorContext) -> Appointment:
        actor.require_any_role("PATIENT")
        slot = self.repository.lock_slot(data.schedule_slot_id)
        if slot is None:
            raise NotFoundError("Schedule slot was not found.", "slot_not_found")
        if slot.schedule.status != ScheduleStatus.ACTIVE or slot.status != SlotStatus.AVAILABLE:
            raise ConflictError("The selected slot is not available.", "slot_unavailable")
        if slot.start_at <= datetime.now(timezone.utc):
            raise BadRequestError("Past slots cannot be booked.", "slot_in_past")
        if self.repository.has_occupied_appointment(slot.id):
            raise ConflictError("The selected slot is already occupied.", "slot_occupied")
        appointment = Appointment(
            patient_id=actor.user_id,
            schedule_slot_id=slot.id,
            status=AppointmentStatus.CONFIRMED,
            booked_at=datetime.now(timezone.utc),
        )
        slot.status = SlotStatus.BOOKED
        self.repository.add(appointment)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("The slot was booked by another request.", "slot_occupied") from exc
        return self.get(appointment.id, actor)

    def cancel(
        self, appointment_id: UUID, data: AppointmentCancel, actor: ActorContext
    ) -> Appointment:
        appointment = self.repository.get(appointment_id, for_update=True)
        if appointment is None:
            raise NotFoundError("Appointment was not found.", "appointment_not_found")
        can_coordinate = actor.has_any_role("STAFF", "ADMIN")
        if appointment.patient_id != actor.user_id and not can_coordinate:
            raise ForbiddenError()
        if appointment.status != AppointmentStatus.CONFIRMED:
            raise ConflictError("Only confirmed appointments can be cancelled.", "invalid_appointment_state")
        if not can_coordinate and appointment.schedule_slot.start_at <= datetime.now(timezone.utc):
            raise ConflictError("The appointment can no longer be cancelled by the patient.", "cancellation_closed")
        appointment.status = AppointmentStatus.CANCELLED
        appointment.cancelled_at = datetime.now(timezone.utc)
        appointment.cancelled_by = actor.user_id
        appointment.cancellation_reason = data.reason.strip()
        appointment.schedule_slot.status = SlotStatus.AVAILABLE
        self.session.add(
            AuditLog(
                actor_user_id=actor.user_id,
                action="APPOINTMENT_CANCELLED",
                entity_type="appointment",
                entity_id=appointment.id,
                audit_metadata={"previous_status": "CONFIRMED", "new_status": "CANCELLED"},
            )
        )
        self.session.commit()
        return self.get(appointment.id, actor)

    def set_outcome(
        self, appointment_id: UUID, data: AppointmentOutcome, actor: ActorContext
    ) -> Appointment:
        actor.require_any_role("DOCTOR")
        if data.status not in {AppointmentStatus.COMPLETED, AppointmentStatus.NO_SHOW}:
            raise BadRequestError("Outcome must be COMPLETED or NO_SHOW.", "invalid_outcome")
        appointment = self.repository.get(appointment_id, for_update=True)
        if appointment is None:
            raise NotFoundError("Appointment was not found.", "appointment_not_found")
        if self._doctor_user_id(appointment) != actor.user_id:
            raise ForbiddenError()
        if appointment.status != AppointmentStatus.CONFIRMED:
            raise ConflictError("Only confirmed appointments can receive an outcome.", "invalid_appointment_state")
        now = datetime.now(timezone.utc)
        appointment.status = data.status
        if data.status == AppointmentStatus.COMPLETED:
            appointment.completed_at = now
        else:
            appointment.no_show_at = now
        # BOOKED is intentionally retained as the non-available terminal slot state in this schema.
        self.session.add(
            AuditLog(
                actor_user_id=actor.user_id,
                action=f"APPOINTMENT_{data.status.value}",
                entity_type="appointment",
                entity_id=appointment.id,
                audit_metadata={"previous_status": "CONFIRMED", "new_status": data.status.value},
            )
        )
        self.session.commit()
        return self.get(appointment.id, actor)
