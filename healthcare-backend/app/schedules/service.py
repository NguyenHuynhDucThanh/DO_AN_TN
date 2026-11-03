"""Schedule validation, overlap serialization, and deterministic slot generation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.context import ActorContext
from app.core.errors import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.models.care import DoctorSchedule, ScheduleSlot
from app.models.enums import ScheduleStatus, SlotStatus
from app.schedules.repository import ScheduleRepository
from app.schedules.schemas import ScheduleCreate, ScheduleUpdate, SlotStatusUpdate


class ScheduleService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ScheduleRepository(session)

    @staticmethod
    def _validate_range(start_at: datetime, end_at: datetime, duration: int) -> None:
        if end_at <= start_at:
            raise BadRequestError("Schedule end must be after start.", "invalid_schedule_time")
        seconds = int((end_at - start_at).total_seconds())
        if seconds % (duration * 60) != 0:
            raise BadRequestError(
                "Schedule range must be exactly divisible by slot duration.",
                "invalid_slot_duration",
            )

    @staticmethod
    def _authorize_doctor(actor: ActorContext, doctor_user_id: UUID) -> None:
        if actor.has_any_role("STAFF", "ADMIN"):
            return
        if actor.has_any_role("DOCTOR") and actor.user_id == doctor_user_id:
            return
        raise ForbiddenError()

    def list(self, doctor_id: UUID | None = None) -> list[DoctorSchedule]:
        return self.repository.list(doctor_id)

    def get(self, schedule_id: UUID) -> DoctorSchedule:
        schedule = self.repository.get(schedule_id)
        if schedule is None:
            raise NotFoundError("Schedule was not found.", "schedule_not_found")
        return schedule

    def create(self, data: ScheduleCreate, actor: ActorContext) -> DoctorSchedule:
        doctor = self.repository.get_doctor(data.doctor_id)
        if doctor is None:
            raise NotFoundError("Doctor was not found.", "doctor_not_found")
        self._authorize_doctor(actor, doctor.user_id)
        self._validate_range(data.start_at, data.end_at, data.slot_duration_minutes)
        if data.start_at <= datetime.now(timezone.utc):
            raise BadRequestError("New schedules must start in the future.", "schedule_in_past")
        self.repository.lock_doctor(doctor.id)
        if self.repository.has_overlap(doctor.id, data.start_at, data.end_at):
            self.session.rollback()
            raise ConflictError("The doctor already has an overlapping schedule.", "schedule_overlap")
        schedule = DoctorSchedule(**data.model_dump(), status=ScheduleStatus.ACTIVE)
        self.repository.add(schedule)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("The schedule conflicts with existing data.", "schedule_conflict") from exc
        self.session.refresh(schedule)
        return schedule

    def update(
        self, schedule_id: UUID, data: ScheduleUpdate, actor: ActorContext
    ) -> DoctorSchedule:
        schedule = self.repository.get(schedule_id, for_update=True)
        if schedule is None:
            raise NotFoundError("Schedule was not found.", "schedule_not_found")
        self._authorize_doctor(actor, schedule.doctor.user_id)
        changes = data.model_dump(exclude_unset=True)
        interval_fields = {"start_at", "end_at", "slot_duration_minutes"}
        if interval_fields.intersection(changes) and self.repository.list_slots(schedule.id):
            self.session.rollback()
            raise ConflictError("A schedule with generated slots cannot change its interval.", "schedule_has_slots")
        start_at = changes.get("start_at", schedule.start_at)
        end_at = changes.get("end_at", schedule.end_at)
        duration = changes.get("slot_duration_minutes", schedule.slot_duration_minutes)
        self._validate_range(start_at, end_at, duration)
        self.repository.lock_doctor(schedule.doctor_id)
        if changes.get("status", schedule.status) == ScheduleStatus.ACTIVE and self.repository.has_overlap(
            schedule.doctor_id, start_at, end_at, schedule.id
        ):
            self.session.rollback()
            raise ConflictError("The doctor already has an overlapping schedule.", "schedule_overlap")
        for field, value in changes.items():
            setattr(schedule, field, value)
        if schedule.status == ScheduleStatus.CANCELLED:
            for slot in self.repository.list_slots(schedule.id):
                if slot.status == SlotStatus.AVAILABLE:
                    slot.status = SlotStatus.BLOCKED
        self.session.commit()
        self.session.refresh(schedule)
        return schedule

    def generate_slots(self, schedule_id: UUID, actor: ActorContext) -> list[ScheduleSlot]:
        schedule = self.repository.get(schedule_id, for_update=True)
        if schedule is None:
            raise NotFoundError("Schedule was not found.", "schedule_not_found")
        self._authorize_doctor(actor, schedule.doctor.user_id)
        if schedule.status != ScheduleStatus.ACTIVE:
            raise ConflictError("Slots cannot be generated for a cancelled schedule.", "schedule_cancelled")
        if self.repository.list_slots(schedule.id):
            raise ConflictError("Slots have already been generated.", "slots_exist")
        self._validate_range(schedule.start_at, schedule.end_at, schedule.slot_duration_minutes)
        step = timedelta(minutes=schedule.slot_duration_minutes)
        cursor = schedule.start_at
        while cursor < schedule.end_at:
            self.session.add(
                ScheduleSlot(
                    schedule_id=schedule.id,
                    start_at=cursor,
                    end_at=cursor + step,
                    status=SlotStatus.AVAILABLE,
                )
            )
            cursor += step
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("Duplicate slots were detected.", "duplicate_slots") from exc
        return self.repository.list_slots(schedule.id)

    def available_slots(
        self,
        from_at: datetime,
        to_at: datetime,
        doctor_id: UUID | None = None,
        specialty_id: UUID | None = None,
    ) -> list[ScheduleSlot]:
        if to_at <= from_at:
            raise BadRequestError("The search end must be after its start.", "invalid_time_range")
        return self.repository.available_slots(from_at, to_at, doctor_id, specialty_id)

    def get_slot(self, slot_id: UUID) -> ScheduleSlot:
        """Return one slot with its business relationships for read-only adapters."""
        slot = self.repository.get_slot(slot_id)
        if slot is None:
            raise NotFoundError("Schedule slot was not found.", "slot_not_found")
        return slot

    def set_slot_status(
        self, slot_id: UUID, data: SlotStatusUpdate, actor: ActorContext
    ) -> ScheduleSlot:
        slot = self.repository.get_slot(slot_id, for_update=True)
        if slot is None:
            raise NotFoundError("Schedule slot was not found.", "slot_not_found")
        self._authorize_doctor(actor, slot.schedule.doctor.user_id)
        if slot.status == SlotStatus.BOOKED:
            raise ConflictError("A booked slot cannot be blocked or unblocked.", "slot_booked")
        slot.status = SlotStatus.BLOCKED if data.blocked else SlotStatus.AVAILABLE
        self.session.commit()
        self.session.refresh(slot)
        return slot
