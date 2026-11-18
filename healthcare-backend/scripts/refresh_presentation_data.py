"""Remove browser-test artifacts and rebuild clean synthetic presentation data."""

from __future__ import annotations

from pathlib import Path
import sys

from sqlalchemy import delete, or_, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import get_session_factory
from app.models import (
    Appointment,
    AuditLog,
    Doctor,
    DoctorSchedule,
    HandoffRequest,
    MedicalRecord,
    RefreshSession,
    ScheduleSlot,
    Specialty,
    User,
    UserRole,
)
from scripts.seed_demo import seed


def refresh() -> None:
    with get_session_factory()() as session, session.begin():
        target_users = list(
            session.scalars(
                select(User).where(
                    or_(
                        User.email.like("workflow.%@example.invalid"),
                        User.email == "phase5.browser@example.invalid",
                    )
                )
            )
        )
        target_user_ids = [user.id for user in target_users]
        target_doctor_ids = list(session.scalars(select(Doctor.id).where(Doctor.user_id.in_(target_user_ids))))
        target_schedule_ids = list(
            session.scalars(select(DoctorSchedule.id).where(DoctorSchedule.doctor_id.in_(target_doctor_ids)))
        )
        target_slot_ids = list(
            session.scalars(select(ScheduleSlot.id).where(ScheduleSlot.schedule_id.in_(target_schedule_ids)))
        )
        target_appointment_ids = list(
            session.scalars(
                select(Appointment.id).where(
                    or_(
                        Appointment.patient_id.in_(target_user_ids),
                        Appointment.schedule_slot_id.in_(target_slot_ids),
                    )
                )
            )
        )
        target_record_ids = list(
            session.scalars(
                select(MedicalRecord.id).where(
                    or_(
                        MedicalRecord.appointment_id.in_(target_appointment_ids),
                        MedicalRecord.created_by.in_(target_user_ids),
                        MedicalRecord.updated_by.in_(target_user_ids),
                    )
                )
            )
        )

        audit_entity_ids = (
            target_record_ids + target_appointment_ids + target_slot_ids + target_schedule_ids
            + target_doctor_ids + target_user_ids
        )
        if audit_entity_ids or target_user_ids:
            session.execute(
                delete(AuditLog).where(
                    or_(AuditLog.entity_id.in_(audit_entity_ids), AuditLog.actor_user_id.in_(target_user_ids))
                )
            )
        session.execute(delete(MedicalRecord).where(MedicalRecord.id.in_(target_record_ids)))
        session.execute(delete(Appointment).where(Appointment.id.in_(target_appointment_ids)))
        session.execute(delete(ScheduleSlot).where(ScheduleSlot.schedule_id.in_(target_schedule_ids)))
        session.execute(delete(DoctorSchedule).where(DoctorSchedule.id.in_(target_schedule_ids)))
        session.execute(delete(Doctor).where(Doctor.id.in_(target_doctor_ids)))
        session.execute(delete(HandoffRequest).where(HandoffRequest.requester_id.in_(target_user_ids)))
        session.execute(delete(RefreshSession).where(RefreshSession.user_id.in_(target_user_ids)))
        session.execute(delete(UserRole).where(UserRole.user_id.in_(target_user_ids)))
        session.execute(delete(User).where(User.id.in_(target_user_ids)))
        session.execute(delete(Specialty).where(Specialty.code.like("WF_%")))

        print(
            "CLEANED "
            f"users={len(target_user_ids)} doctors={len(target_doctor_ids)} "
            f"appointments={len(target_appointment_ids)} specialties=WF_*"
        )

    seed()


if __name__ == "__main__":
    refresh()
