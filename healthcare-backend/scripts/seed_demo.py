"""Idempotently seed synthetic Phase 2 data; never stores a usable password."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import get_session_factory
from app.models import (
    Appointment,
    AuditLog,
    Doctor,
    DoctorSchedule,
    MedicalRecord,
    Role,
    ScheduleSlot,
    Specialty,
    User,
    UserRole,
)
from app.models.enums import AppointmentStatus, ScheduleStatus, SlotStatus, UserStatus

UNUSABLE_PASSWORD_HASH = "!phase5-auth-not-configured"


def get_or_create(session, model, filters: dict, values: dict):
    instance = session.scalar(select(model).filter_by(**filters))
    if instance is None:
        instance = model(**filters, **values)
        session.add(instance)
        session.flush()
    return instance


def seed() -> None:
    with get_session_factory()() as session, session.begin():
        roles = {}
        for code, name in (
            ("PATIENT", "Người bệnh"),
            ("DOCTOR", "Bác sĩ"),
            ("STAFF", "Nhân viên"),
            ("ADMIN", "Quản trị viên"),
        ):
            roles[code] = get_or_create(
                session, Role, {"code": code},
                {"name": name, "description": "Vai trò demo theo SRS v1.1", "is_active": True},
            )

        specialties = {}
        for code, name, description in (
            ("NOI_TONG_QUAT", "Nội tổng quát", "Khám và tư vấn sức khỏe nội khoa tổng quát."),
            ("DA_LIEU", "Da liễu", "Khám các vấn đề về da, tóc và móng."),
            ("TAI_MUI_HONG", "Tai Mũi Họng", "Khám tai, mũi, họng cơ bản."),
        ):
            specialties[code] = get_or_create(
                session, Specialty, {"code": code},
                {"name": name, "description": description, "is_active": True},
            )

        doctor_user = get_or_create(
            session, User, {"email": "doctor.an@example.invalid"},
            {
                "password_hash": UNUSABLE_PASSWORD_HASH,
                "full_name": "BS. Nguyễn Minh An (Demo)",
                "phone": "0900000001",
                "status": UserStatus.ACTIVE,
            },
        )
        patient = get_or_create(
            session, User, {"email": "patient.lan@example.invalid"},
            {
                "password_hash": UNUSABLE_PASSWORD_HASH,
                "full_name": "Trần Hoàng Lan (Demo)",
                "phone": "0900000002",
                "status": UserStatus.ACTIVE,
            },
        )
        staff = get_or_create(
            session, User, {"email": "staff.demo@example.invalid"},
            {
                "password_hash": UNUSABLE_PASSWORD_HASH,
                "full_name": "Nhân viên Điều phối (Demo)",
                "phone": "0900000003",
                "status": UserStatus.ACTIVE,
            },
        )
        admin = get_or_create(
            session, User, {"email": "admin.demo@example.invalid"},
            {
                "password_hash": UNUSABLE_PASSWORD_HASH,
                "full_name": "Quản trị viên (Demo)",
                "phone": "0900000004",
                "status": UserStatus.ACTIVE,
            },
        )
        for user, role_code in (
            (doctor_user, "DOCTOR"),
            (patient, "PATIENT"),
            (staff, "STAFF"),
            (admin, "ADMIN"),
        ):
            get_or_create(
                session, UserRole, {"user_id": user.id, "role_id": roles[role_code].id}, {"assigned_by": None}
            )

        doctor = get_or_create(
            session, Doctor, {"user_id": doctor_user.id},
            {
                "specialty_id": specialties["NOI_TONG_QUAT"].id,
                "license_number": "DEMO-GP-0001",
                "biography": "Bác sĩ dữ liệu tổng hợp phục vụ kiểm thử và trình diễn.",
                "is_active": True,
            },
        )

        completed_start = datetime(2026, 10, 15, 1, 0, tzinfo=timezone.utc)
        future_start = datetime(2030, 1, 15, 1, 0, tzinfo=timezone.utc)
        completed_schedule = get_or_create(
            session, DoctorSchedule,
            {"doctor_id": doctor.id, "start_at": completed_start, "end_at": completed_start + timedelta(hours=2)},
            {"slot_duration_minutes": 30, "status": ScheduleStatus.ACTIVE},
        )
        future_schedule = get_or_create(
            session, DoctorSchedule,
            {"doctor_id": doctor.id, "start_at": future_start, "end_at": future_start + timedelta(hours=2)},
            {"slot_duration_minutes": 30, "status": ScheduleStatus.ACTIVE},
        )
        completed_slot = get_or_create(
            session, ScheduleSlot,
            {"schedule_id": completed_schedule.id, "start_at": completed_start},
            {"end_at": completed_start + timedelta(minutes=30), "status": SlotStatus.BOOKED},
        )
        future_slot = get_or_create(
            session, ScheduleSlot,
            {"schedule_id": future_schedule.id, "start_at": future_start},
            {"end_at": future_start + timedelta(minutes=30), "status": SlotStatus.BOOKED},
        )

        completed_appointment = get_or_create(
            session, Appointment, {"schedule_slot_id": completed_slot.id},
            {
                "patient_id": patient.id,
                "status": AppointmentStatus.COMPLETED,
                "booked_at": completed_start - timedelta(days=5),
                "completed_at": completed_start + timedelta(minutes=25),
            },
        )
        get_or_create(
            session, Appointment, {"schedule_slot_id": future_slot.id},
            {
                "patient_id": patient.id,
                "status": AppointmentStatus.CONFIRMED,
                "booked_at": datetime(2026, 10, 19, 3, 0, tzinfo=timezone.utc),
            },
        )
        record = get_or_create(
            session, MedicalRecord, {"appointment_id": completed_appointment.id},
            {
                "symptoms": "Dữ liệu demo: mệt nhẹ trong hai ngày.",
                "clinical_notes": "Dữ liệu demo, không phải thông tin người bệnh thật.",
                "doctor_conclusion": "Kết luận demo do bác sĩ nhập: theo dõi sức khỏe tổng quát.",
                "follow_up_instructions": "Nghỉ ngơi và tái khám nếu triệu chứng kéo dài.",
                "created_by": doctor_user.id,
                "updated_by": doctor_user.id,
            },
        )
        existing_audit = session.scalar(
            select(AuditLog).where(
                AuditLog.action == "MEDICAL_RECORD_CREATED",
                AuditLog.entity_type == "medical_record",
                AuditLog.entity_id == record.id,
            )
        )
        if existing_audit is None:
            session.add(
                AuditLog(
                    actor_user_id=doctor_user.id,
                    action="MEDICAL_RECORD_CREATED",
                    entity_type="medical_record",
                    entity_id=record.id,
                    audit_metadata={"source": "phase2_demo_seed"},
                )
            )

    print("PASS: synthetic Phase 2 seed is present and internally consistent.")


if __name__ == "__main__":
    seed()
