"""Idempotently seed synthetic Phase 2 data; never stores a usable password."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

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

SPECIALTY_CATALOG = (
    ("NOI_TONG_QUAT", "Nội tổng quát", "Khám sốt, mệt mỏi, đau đầu, chóng mặt, rối loạn huyết áp và các triệu chứng nội khoa chưa xác định."),
    ("TAI_MUI_HONG", "Tai Mũi Họng", "Khám viêm họng, viêm amidan, viêm xoang, ho, đau tai và các bệnh lý tai mũi họng."),
    ("DA_LIEU", "Da liễu", "Khám vảy nến, mụn, viêm da, dị ứng da và các vấn đề về tóc, da, móng."),
    ("TIEU_HOA_GAN_MAT", "Tiêu hóa - Gan mật", "Khám trào ngược dạ dày, đau bụng, rối loạn tiêu hóa, bệnh gan và bệnh lý tụy."),
    ("TIM_MACH", "Tim mạch", "Khám đau ngực, hồi hộp, tăng huyết áp và đánh giá nguy cơ bệnh tim mạch."),
    ("THAN_KINH", "Thần kinh", "Khám đau đầu, chóng mặt, rối loạn thần kinh thực vật và theo dõi nguy cơ đột quỵ."),
    ("SAN_PHU_KHOA", "Sản phụ khoa", "Khám thai, theo dõi sự phát triển của thai và các vấn đề sức khỏe phụ khoa."),
    ("NHI_KHOA", "Nhi khoa", "Khám bệnh trẻ em, tay chân miệng, chậm tăng cân, chậm phát triển và tư vấn chăm sóc trẻ."),
    ("TRUYEN_NHIEM", "Truyền nhiễm", "Khám và tư vấn COVID-19, sởi, sốt siêu vi, nhiễm ký sinh trùng và phòng bệnh bằng vaccine."),
    ("DINH_DUONG", "Dinh dưỡng", "Tư vấn chế độ ăn, kiểm soát cân nặng và dinh dưỡng cho trẻ em, người lớn hoặc người có bệnh nền."),
)

DOCTOR_CATALOG = (
    ("doctor.an@example.invalid", "BS. Nguyễn Minh An", "0900000001", "NOI_TONG_QUAT", "CCHN-10001", "Khám và tư vấn nội khoa tổng quát.", (8, 0, 12, 0)),
    ("doctor.bao@example.invalid", "BS. Trần Quốc Bảo", "0900000011", "TAI_MUI_HONG", "CCHN-10002", "Khám và điều trị các bệnh lý tai mũi họng.", (13, 30, 17, 30)),
    ("doctor.ha@example.invalid", "BS. Lê Thu Hà", "0900000012", "DA_LIEU", "CCHN-10003", "Khám và tư vấn chăm sóc da, tóc và móng.", (8, 0, 12, 0)),
    ("doctor.nam@example.invalid", "BS. Phạm Hoàng Nam", "0900000013", "TIEU_HOA_GAN_MAT", "CCHN-10004", "Khám các bệnh lý tiêu hóa, gan mật và tụy.", (13, 30, 17, 30)),
    ("doctor.tung@example.invalid", "BS. Võ Thanh Tùng", "0900000014", "TIM_MACH", "CCHN-10005", "Khám và tư vấn các vấn đề tim mạch.", (8, 0, 12, 0)),
    ("doctor.mai@example.invalid", "BS. Đặng Ngọc Mai", "0900000015", "THAN_KINH", "CCHN-10006", "Khám các triệu chứng và bệnh lý thần kinh.", (13, 30, 17, 30)),
    ("doctor.lananh@example.invalid", "BS. Nguyễn Thị Lan Anh", "0900000016", "SAN_PHU_KHOA", "CCHN-10007", "Khám sản khoa, thai kỳ và sức khỏe phụ khoa.", (8, 0, 12, 0)),
    ("doctor.huy@example.invalid", "BS. Bùi Gia Huy", "0900000017", "NHI_KHOA", "CCHN-10008", "Khám và theo dõi sức khỏe trẻ em.", (13, 30, 17, 30)),
    ("doctor.khang@example.invalid", "BS. Hồ Minh Khang", "0900000018", "TRUYEN_NHIEM", "CCHN-10009", "Khám bệnh truyền nhiễm và tư vấn phòng bệnh.", (8, 0, 12, 0)),
    ("doctor.nguyen@example.invalid", "BS. Vũ Thảo Nguyên", "0900000019", "DINH_DUONG", "CCHN-10010", "Tư vấn dinh dưỡng theo độ tuổi và tình trạng sức khỏe.", (13, 30, 17, 30)),
)


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
                {"name": name, "description": "Vai trò người dùng trong hệ thống", "is_active": True},
            )

        specialties = {}
        for code, name, description in SPECIALTY_CATALOG:
            specialties[code] = get_or_create(
                session, Specialty, {"code": code},
                {"name": name, "description": description, "is_active": True},
            )
            specialties[code].name = name
            specialties[code].description = description
            specialties[code].is_active = True

        doctor_user = get_or_create(
            session, User, {"email": "doctor.an@example.invalid"},
            {
                "password_hash": UNUSABLE_PASSWORD_HASH,
                "full_name": "BS. Nguyễn Minh An",
                "phone": "0900000001",
                "status": UserStatus.ACTIVE,
            },
        )
        doctor_user.full_name = "BS. Nguyễn Minh An"
        patient = get_or_create(
            session, User, {"email": "patient.lan@example.invalid"},
            {
                "password_hash": UNUSABLE_PASSWORD_HASH,
                "full_name": "Trần Hoàng Lan",
                "phone": "0900000002",
                "status": UserStatus.ACTIVE,
            },
        )
        patient.full_name = "Trần Hoàng Lan"
        staff = get_or_create(
            session, User, {"email": "staff.demo@example.invalid"},
            {
                "password_hash": UNUSABLE_PASSWORD_HASH,
                "full_name": "Nguyễn Thị Hồng",
                "phone": "0900000003",
                "status": UserStatus.ACTIVE,
            },
        )
        staff.full_name = "Nguyễn Thị Hồng"
        admin = get_or_create(
            session, User, {"email": "admin.demo@example.invalid"},
            {
                "password_hash": UNUSABLE_PASSWORD_HASH,
                "full_name": "Quản trị viên hệ thống",
                "phone": "0900000004",
                "status": UserStatus.ACTIVE,
            },
        )
        admin.full_name = "Quản trị viên hệ thống"
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
        doctor.license_number = "CCHN-10001"
        doctor.biography = "Khám và tư vấn nội khoa tổng quát."

        doctors = {"doctor.an@example.invalid": doctor}
        for email, full_name, phone, specialty_code, license_number, biography, _shift in DOCTOR_CATALOG[1:]:
            user = get_or_create(
                session, User, {"email": email},
                {
                    "password_hash": UNUSABLE_PASSWORD_HASH,
                    "full_name": full_name,
                    "phone": phone,
                    "status": UserStatus.ACTIVE,
                },
            )
            user.full_name = full_name
            user.phone = phone
            user.status = UserStatus.ACTIVE
            get_or_create(
                session, UserRole, {"user_id": user.id, "role_id": roles["DOCTOR"].id}, {"assigned_by": None}
            )
            profile = get_or_create(
                session, Doctor, {"user_id": user.id},
                {
                    "specialty_id": specialties[specialty_code].id,
                    "license_number": license_number,
                    "biography": biography,
                    "is_active": True,
                },
            )
            profile.specialty_id = specialties[specialty_code].id
            profile.license_number = license_number
            profile.biography = biography
            profile.is_active = True
            doctors[email] = profile

        local_tz = ZoneInfo("Asia/Ho_Chi_Minh")
        first_day = datetime.now(local_tz).date() + timedelta(days=1)
        for email, _full_name, _phone, _specialty_code, _license_number, _biography, shift in DOCTOR_CATALOG:
            profile = doctors[email]
            start_hour, start_minute, end_hour, end_minute = shift
            for day_offset in range(31):
                work_day = first_day + timedelta(days=day_offset)
                if work_day.weekday() >= 5:
                    continue
                start_local = datetime.combine(work_day, time(start_hour, start_minute), tzinfo=local_tz)
                end_local = datetime.combine(work_day, time(end_hour, end_minute), tzinfo=local_tz)
                start_at = start_local.astimezone(timezone.utc)
                end_at = end_local.astimezone(timezone.utc)
                schedule = get_or_create(
                    session, DoctorSchedule,
                    {"doctor_id": profile.id, "start_at": start_at, "end_at": end_at},
                    {"slot_duration_minutes": 30, "status": ScheduleStatus.ACTIVE},
                )
                schedule.status = ScheduleStatus.ACTIVE
                cursor = start_at
                while cursor < end_at:
                    get_or_create(
                        session, ScheduleSlot,
                        {"schedule_id": schedule.id, "start_at": cursor},
                        {"end_at": cursor + timedelta(minutes=30), "status": SlotStatus.AVAILABLE},
                    )
                    cursor += timedelta(minutes=30)

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
                "symptoms": "Mệt nhẹ trong hai ngày.",
                "clinical_notes": "Ghi nhận sức khỏe tổng quát, chưa thấy dấu hiệu bất thường.",
                "doctor_conclusion": "Theo dõi sức khỏe tổng quát.",
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

    print("PASS: synthetic presentation catalog and 31-day schedules are present.")


if __name__ == "__main__":
    seed()
