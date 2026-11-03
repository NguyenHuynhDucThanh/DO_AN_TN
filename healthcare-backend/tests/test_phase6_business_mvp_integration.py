"""Phase 6 Business MVP concurrency, lifecycle, and authenticated E2E tests."""

from __future__ import annotations

import json
import secrets
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

import app.appointments.service as appointment_service_module
from app.appointments.schemas import AppointmentCancel, AppointmentCreate, AppointmentOutcome
from app.appointments.service import AppointmentService
from app.ai.tools.executor import ToolExecutor
from app.auth.context import ActorContext
from app.auth.passwords import hash_password
from app.core.config import get_settings
from app.core.errors import BadRequestError, ConflictError, ForbiddenError
from app.handoffs.service import HandoffService
from app.main import create_app
from app.models.care import Appointment, Doctor, DoctorSchedule, ScheduleSlot, Specialty
from app.models.enums import AppointmentStatus, ScheduleStatus, SlotStatus, UserStatus
from app.models.identity import RefreshSession, Role, User, UserRole
from app.models.medical_record import MedicalRecord
from app.models.operations import AuditLog, HandoffRequest
from app.schedules.schemas import ScheduleCreate
from app.schedules.service import ScheduleService

pytestmark = pytest.mark.integration


@dataclass(slots=True)
class Phase6Data:
    prefix: str
    doctor: Doctor
    other_doctor: Doctor
    doctor_user: User
    other_doctor_user: User
    patients: list[User]
    staff: User
    admin: User
    passwords: dict[UUID, str]
    schedule: DoctorSchedule
    slots: list[ScheduleSlot]

    def actor(self, user: User, role: str) -> ActorContext:
        return ActorContext(user.id, frozenset({role}))


@pytest.mark.anyio
async def test_phase9_explicit_confirmation_delegates_real_booking(
    real_database, phase6_data: "Phase6Data"
):
    """No Appointment exists before confirmation; the existing service creates it after."""
    patient = phase6_data.patients[0]
    slot_id = phase6_data.slots[9].id
    with Session(real_database, expire_on_commit=False) as session:
        tools = ToolExecutor(session, get_settings())
        prepared = await tools.execute(
            "create_booking",
            {"slot_id": str(slot_id)},
            phase6_data.actor(patient, "PATIENT"),
        )
        assert prepared.status == "CONFIRMATION_REQUIRED"
        assert session.scalar(
            select(Appointment.id).where(Appointment.schedule_slot_id == slot_id)
        ) is None
        appointment = tools.confirm_booking(
            prepared.data["confirmation_token"],
            phase6_data.actor(patient, "PATIENT"),
        )
        assert appointment.patient_id == patient.id
        assert appointment.schedule_slot_id == slot_id
        assert appointment.status == AppointmentStatus.CONFIRMED


def test_phase10_risk_handoff_reuses_persistent_workflow(
    real_database, phase6_data: "Phase6Data"
):
    patient = phase6_data.patients[0]
    with Session(real_database, expire_on_commit=False) as session:
        handoff = HandoffService(session).create_risk_alert(
            ("RISK-RESPIRATORY",), phase6_data.actor(patient, "PATIENT")
        )
        assert handoff.requester_id == patient.id
        assert handoff.source == "RISK_ALERT"
        assert handoff.priority.value == "URGENT"
        assert handoff.status.value == "PENDING"
        assert "RISK-RESPIRATORY" in handoff.reason
        assert "không thở được" not in handoff.reason.casefold()


def _create_user(
    session: Session,
    *,
    prefix: str,
    label: str,
    role_code: str,
    passwords: dict[UUID, str],
) -> User:
    role = session.scalar(select(Role).where(Role.code == role_code))
    assert role is not None
    password = f"{secrets.token_urlsafe(18)}aA1"
    user = User(
        email=f"{prefix}-{label}@example.invalid",
        password_hash=hash_password(password),
        full_name=f"Phase 6 {label} Synthetic",
        phone="0900000066",
        status=UserStatus.ACTIVE,
    )
    session.add(user)
    session.flush()
    session.add(UserRole(user_id=user.id, role_id=role.id))
    passwords[user.id] = password
    return user


def _cleanup_phase6_data(engine, prefix: str) -> None:
    with Session(engine) as session:
        user_ids = list(
            session.scalars(select(User.id).where(User.email.like(f"{prefix}%")))
        )
        if not user_ids:
            return
        doctor_ids = list(
            session.scalars(select(Doctor.id).where(Doctor.user_id.in_(user_ids)))
        )
        schedule_ids = (
            list(
                session.scalars(
                    select(DoctorSchedule.id).where(DoctorSchedule.doctor_id.in_(doctor_ids))
                )
            )
            if doctor_ids
            else []
        )
        slot_ids = (
            list(
                session.scalars(
                    select(ScheduleSlot.id).where(ScheduleSlot.schedule_id.in_(schedule_ids))
                )
            )
            if schedule_ids
            else []
        )
        appointment_ids = list(
            session.scalars(
                select(Appointment.id).where(
                    (Appointment.patient_id.in_(user_ids))
                    | (Appointment.schedule_slot_id.in_(slot_ids) if slot_ids else False)
                )
            )
        )
        record_ids = (
            list(
                session.scalars(
                    select(MedicalRecord.id).where(
                        MedicalRecord.appointment_id.in_(appointment_ids)
                    )
                )
            )
            if appointment_ids
            else []
        )
        session.execute(delete(AuditLog).where(AuditLog.actor_user_id.in_(user_ids)))
        session.execute(
            delete(HandoffRequest).where(
                (HandoffRequest.requester_id.in_(user_ids))
                | (HandoffRequest.assigned_to.in_(user_ids))
            )
        )
        if record_ids:
            session.execute(delete(MedicalRecord).where(MedicalRecord.id.in_(record_ids)))
        if appointment_ids:
            session.execute(delete(Appointment).where(Appointment.id.in_(appointment_ids)))
        if slot_ids:
            session.execute(delete(ScheduleSlot).where(ScheduleSlot.id.in_(slot_ids)))
        if schedule_ids:
            session.execute(
                delete(DoctorSchedule).where(DoctorSchedule.id.in_(schedule_ids))
            )
        if doctor_ids:
            session.execute(delete(Doctor).where(Doctor.id.in_(doctor_ids)))
        session.execute(delete(RefreshSession).where(RefreshSession.user_id.in_(user_ids)))
        session.execute(delete(UserRole).where(UserRole.user_id.in_(user_ids)))
        session.execute(delete(User).where(User.id.in_(user_ids)))
        session.commit()


@pytest.fixture
def phase6_data(real_database):
    prefix = f"phase6-{uuid4().hex}"
    passwords: dict[UUID, str] = {}
    try:
        with Session(real_database, expire_on_commit=False) as session:
            specialty = session.scalar(select(Specialty).order_by(Specialty.id).limit(1))
            assert specialty is not None
            doctor_user = _create_user(
                session,
                prefix=prefix,
                label="doctor",
                role_code="DOCTOR",
                passwords=passwords,
            )
            other_doctor_user = _create_user(
                session,
                prefix=prefix,
                label="doctor-other",
                role_code="DOCTOR",
                passwords=passwords,
            )
            patients = [
                _create_user(
                    session,
                    prefix=prefix,
                    label=f"patient-{index}",
                    role_code="PATIENT",
                    passwords=passwords,
                )
                for index in range(6)
            ]
            staff = _create_user(
                session,
                prefix=prefix,
                label="staff",
                role_code="STAFF",
                passwords=passwords,
            )
            admin = _create_user(
                session,
                prefix=prefix,
                label="admin",
                role_code="ADMIN",
                passwords=passwords,
            )
            doctor = Doctor(
                user_id=doctor_user.id,
                specialty_id=specialty.id,
                license_number=f"P6-{uuid4().hex[:12]}",
                biography="Synthetic Phase 6 concurrency doctor",
                is_active=True,
            )
            other_doctor = Doctor(
                user_id=other_doctor_user.id,
                specialty_id=specialty.id,
                license_number=f"P6-{uuid4().hex[:12]}",
                biography="Synthetic Phase 6 ownership doctor",
                is_active=True,
            )
            session.add_all([doctor, other_doctor])
            session.flush()
            start = datetime(2035, 6, 10, 1, 0, tzinfo=timezone.utc)
            schedule = DoctorSchedule(
                doctor_id=doctor.id,
                start_at=start,
                end_at=start + timedelta(hours=5),
                slot_duration_minutes=30,
                status=ScheduleStatus.ACTIVE,
            )
            session.add(schedule)
            session.flush()
            slots = [
                ScheduleSlot(
                    schedule_id=schedule.id,
                    start_at=start + timedelta(minutes=30 * index),
                    end_at=start + timedelta(minutes=30 * (index + 1)),
                    status=SlotStatus.AVAILABLE,
                )
                for index in range(10)
            ]
            session.add_all(slots)
            session.commit()
            yield Phase6Data(
                prefix=prefix,
                doctor=doctor,
                other_doctor=other_doctor,
                doctor_user=doctor_user,
                other_doctor_user=other_doctor_user,
                patients=patients,
                staff=staff,
                admin=admin,
                passwords=passwords,
                schedule=schedule,
                slots=slots,
            )
    finally:
        _cleanup_phase6_data(real_database, prefix)


def test_concurrent_booking_allows_exactly_one_success(real_database, phase6_data: Phase6Data):
    slot_id = phase6_data.slots[0].id
    barrier = Barrier(5)

    def book(patient: User):
        with Session(real_database, expire_on_commit=False) as session:
            barrier.wait(timeout=10)
            try:
                appointment = AppointmentService(session).create(
                    AppointmentCreate(schedule_slot_id=slot_id),
                    phase6_data.actor(patient, "PATIENT"),
                )
                return "success", appointment.id, None
            except ConflictError as exc:
                return "conflict", None, (exc.status_code, exc.code)

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(book, phase6_data.patients[:5]))

    assert [result[0] for result in results].count("success") == 1
    conflicts = [result for result in results if result[0] == "conflict"]
    assert len(conflicts) == 4
    assert all(result[2] == (409, "slot_unavailable") for result in conflicts)
    with Session(real_database) as session:
        occupied = list(
            session.scalars(
                select(Appointment).where(
                    Appointment.schedule_slot_id == slot_id,
                    Appointment.status.in_(
                        [
                            AppointmentStatus.CONFIRMED,
                            AppointmentStatus.COMPLETED,
                            AppointmentStatus.NO_SHOW,
                        ]
                    ),
                )
            )
        )
        slot = session.get(ScheduleSlot, slot_id)
        assert len(occupied) == 1
        assert slot is not None and slot.status == SlotStatus.BOOKED
        index_definition = session.scalar(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE tablename = 'appointments' "
                "AND indexname = 'uq_appointments_occupied_slot'"
            )
        )
        assert index_definition is not None
        normalized_index = " ".join(index_definition.upper().split())
        assert "UNIQUE INDEX" in normalized_index
        assert all(status in normalized_index for status in ("CONFIRMED", "COMPLETED", "NO_SHOW"))


def test_schedule_overlap_race_is_serialized_and_adjacent_ranges_are_allowed(
    real_database, phase6_data: Phase6Data
):
    actor = phase6_data.actor(phase6_data.doctor_user, "DOCTOR")
    race_start = datetime(2036, 2, 1, 8, 0, tzinfo=timezone.utc)
    barrier = Barrier(2)
    ranges = [
        (race_start, race_start + timedelta(hours=2)),
        (race_start + timedelta(hours=1), race_start + timedelta(hours=3)),
    ]

    def create_range(interval: tuple[datetime, datetime]):
        with Session(real_database, expire_on_commit=False) as session:
            barrier.wait(timeout=10)
            try:
                schedule = ScheduleService(session).create(
                    ScheduleCreate(
                        doctor_id=phase6_data.doctor.id,
                        start_at=interval[0],
                        end_at=interval[1],
                        slot_duration_minutes=30,
                    ),
                    actor,
                )
                return "success", schedule.id
            except ConflictError as exc:
                assert exc.status_code == 409
                assert exc.code == "schedule_overlap"
                return "conflict", None

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(create_range, ranges))
    assert sorted(result[0] for result in results) == ["conflict", "success"]

    adjacent_start = datetime(2036, 3, 1, 8, 0, tzinfo=timezone.utc)
    with Session(real_database, expire_on_commit=False) as session:
        schedules = ScheduleService(session)
        first = schedules.create(
            ScheduleCreate(
                doctor_id=phase6_data.doctor.id,
                start_at=adjacent_start,
                end_at=adjacent_start + timedelta(hours=2),
                slot_duration_minutes=30,
            ),
            actor,
        )
        second = schedules.create(
            ScheduleCreate(
                doctor_id=phase6_data.doctor.id,
                start_at=adjacent_start + timedelta(hours=2),
                end_at=adjacent_start + timedelta(hours=4),
                slot_duration_minutes=30,
            ),
            actor,
        )
        assert first.end_at == second.start_at


def test_appointment_transitions_keep_slot_state_consistent(
    real_database, phase6_data: Phase6Data
):
    patient = phase6_data.actor(phase6_data.patients[0], "PATIENT")
    doctor = phase6_data.actor(phase6_data.doctor_user, "DOCTOR")
    with Session(real_database, expire_on_commit=False) as session:
        service = AppointmentService(session)

        completed = service.create(
            AppointmentCreate(schedule_slot_id=phase6_data.slots[1].id), patient
        )
        completed = service.set_outcome(
            completed.id, AppointmentOutcome(status=AppointmentStatus.COMPLETED), doctor
        )
        assert completed.status == AppointmentStatus.COMPLETED
        assert completed.schedule_slot.status == SlotStatus.BOOKED
        with pytest.raises(ConflictError, match="Only confirmed"):
            service.cancel(completed.id, AppointmentCancel(reason="Too late"), patient)
        with pytest.raises(ConflictError, match="Only confirmed"):
            service.set_outcome(
                completed.id, AppointmentOutcome(status=AppointmentStatus.NO_SHOW), doctor
            )

        no_show = service.create(
            AppointmentCreate(schedule_slot_id=phase6_data.slots[2].id), patient
        )
        no_show = service.set_outcome(
            no_show.id, AppointmentOutcome(status=AppointmentStatus.NO_SHOW), doctor
        )
        assert no_show.status == AppointmentStatus.NO_SHOW
        assert no_show.schedule_slot.status == SlotStatus.BOOKED
        with pytest.raises(ConflictError, match="Only confirmed"):
            service.cancel(no_show.id, AppointmentCancel(reason="Too late"), patient)

        cancelled = service.create(
            AppointmentCreate(schedule_slot_id=phase6_data.slots[3].id), patient
        )
        with pytest.raises(ForbiddenError):
            service.cancel(
                cancelled.id,
                AppointmentCancel(reason="Not the owner"),
                phase6_data.actor(phase6_data.patients[1], "PATIENT"),
            )
        cancelled = service.cancel(
            cancelled.id, AppointmentCancel(reason="Synthetic cancellation"), patient
        )
        assert cancelled.status == AppointmentStatus.CANCELLED
        assert cancelled.schedule_slot.status == SlotStatus.AVAILABLE
        with pytest.raises(ConflictError, match="Only confirmed"):
            service.set_outcome(
                cancelled.id, AppointmentOutcome(status=AppointmentStatus.COMPLETED), doctor
            )
        with pytest.raises(BadRequestError):
            service.set_outcome(
                cancelled.id, AppointmentOutcome(status=AppointmentStatus.CANCELLED), doctor
            )


def test_patient_cancellation_boundary_is_strictly_before_start(
    real_database, phase6_data: Phase6Data, monkeypatch: pytest.MonkeyPatch
):
    patient = phase6_data.actor(phase6_data.patients[0], "PATIENT")
    with Session(real_database, expire_on_commit=False) as session:
        service = AppointmentService(session)
        closed = service.create(
            AppointmentCreate(schedule_slot_id=phase6_data.slots[4].id), patient
        )
        allowed = service.create(
            AppointmentCreate(schedule_slot_id=phase6_data.slots[5].id), patient
        )

        clock = {"now": phase6_data.slots[4].start_at}

        class FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                current = clock["now"]
                return current.astimezone(tz) if tz is not None else current.replace(tzinfo=None)

        monkeypatch.setattr(appointment_service_module, "datetime", FrozenDateTime)
        with pytest.raises(ConflictError) as at_start:
            service.cancel(closed.id, AppointmentCancel(reason="At boundary"), patient)
        assert at_start.value.code == "cancellation_closed"

        clock["now"] = phase6_data.slots[5].start_at - timedelta(microseconds=1)
        cancelled = service.cancel(
            allowed.id, AppointmentCancel(reason="Before boundary"), patient
        )
        assert cancelled.status == AppointmentStatus.CANCELLED
        assert cancelled.schedule_slot.status == SlotStatus.AVAILABLE


def _csrf_headers(client: AsyncClient) -> dict[str, str]:
    settings = get_settings()
    token = client.cookies.get(settings.csrf_cookie_name)
    assert token
    return {"Origin": settings.frontend_origin, "X-CSRF-Token": token}


async def _login(client: AsyncClient, user: User, password: str) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": password},
        headers={"Origin": get_settings().frontend_origin},
    )
    assert response.status_code == 200, response.text


@pytest.mark.anyio
async def test_authenticated_business_and_medical_record_e2e(
    real_database, phase6_data: Phase6Data
):
    app = create_app()
    settings = get_settings()
    patient_password = f"{secrets.token_urlsafe(18)}aA1"
    patient_email = f"{phase6_data.prefix}-registered@example.invalid"
    transport = ASGITransport(app=app)

    async with (
        AsyncClient(transport=transport, base_url="http://testserver") as patient_client,
        AsyncClient(transport=transport, base_url="http://testserver") as doctor_client,
        AsyncClient(transport=transport, base_url="http://testserver") as other_doctor_client,
        AsyncClient(transport=transport, base_url="http://testserver") as other_patient_client,
        AsyncClient(transport=transport, base_url="http://testserver") as staff_client,
        AsyncClient(transport=transport, base_url="http://testserver") as admin_client,
    ):
        registered = await patient_client.post(
            "/api/v1/auth/register",
            json={
                "email": patient_email,
                "password": patient_password,
                "full_name": "Phase 6 Registered Patient",
                "phone": "0900000067",
            },
            headers={"Origin": settings.frontend_origin},
        )
        assert registered.status_code == 201, registered.text
        patient_id = UUID(registered.json()["user"]["id"])

        logged_out = await patient_client.post(
            "/api/v1/auth/logout", headers=_csrf_headers(patient_client)
        )
        assert logged_out.status_code == 204
        login = await patient_client.post(
            "/api/v1/auth/login",
            json={"email": patient_email.upper(), "password": patient_password},
            headers={"Origin": settings.frontend_origin},
        )
        assert login.status_code == 200

        specialties = await patient_client.get("/api/v1/specialties")
        doctors = await patient_client.get("/api/v1/doctors")
        slots = await patient_client.get(
            "/api/v1/schedules/available-slots",
            params={
                "from_at": phase6_data.schedule.start_at.isoformat(),
                "to_at": phase6_data.schedule.end_at.isoformat(),
                "doctor_id": str(phase6_data.doctor.id),
            },
        )
        assert specialties.status_code == doctors.status_code == slots.status_code == 200
        assert len(slots.json()) == 10

        first_booking = await patient_client.post(
            "/api/v1/appointments",
            json={"schedule_slot_id": str(phase6_data.slots[6].id)},
            headers=_csrf_headers(patient_client),
        )
        assert first_booking.status_code == 201, first_booking.text
        first_appointment_id = first_booking.json()["id"]
        cancelled = await patient_client.post(
            f"/api/v1/appointments/{first_appointment_id}/cancel",
            json={"reason": "Phase 6 synthetic cancellation"},
            headers=_csrf_headers(patient_client),
        )
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "CANCELLED"

        second_booking = await patient_client.post(
            "/api/v1/appointments",
            json={"schedule_slot_id": str(phase6_data.slots[7].id)},
            headers=_csrf_headers(patient_client),
        )
        assert second_booking.status_code == 201, second_booking.text
        appointment_id = second_booking.json()["id"]

        await _login(
            doctor_client,
            phase6_data.doctor_user,
            phase6_data.passwords[phase6_data.doctor_user.id],
        )
        medical_payload = {
            "appointment_id": appointment_id,
            "symptoms": "Synthetic symptom Phase 6",
            "clinical_notes": "Synthetic clinical note Phase 6",
            "doctor_conclusion": "Synthetic doctor conclusion Phase 6",
            "follow_up_instructions": "Synthetic follow-up Phase 6",
        }
        before_completed = await doctor_client.post(
            "/api/v1/medical-records",
            json=medical_payload,
            headers=_csrf_headers(doctor_client),
        )
        assert before_completed.status_code == 409
        assert before_completed.json()["error"]["code"] == "appointment_not_completed"

        await _login(
            other_doctor_client,
            phase6_data.other_doctor_user,
            phase6_data.passwords[phase6_data.other_doctor_user.id],
        )
        completed = await doctor_client.post(
            f"/api/v1/appointments/{appointment_id}/outcome",
            json={"status": "COMPLETED"},
            headers=_csrf_headers(doctor_client),
        )
        assert completed.status_code == 200
        assert completed.json()["status"] == "COMPLETED"
        wrong_doctor_create = await other_doctor_client.post(
            "/api/v1/medical-records",
            json=medical_payload,
            headers=_csrf_headers(other_doctor_client),
        )
        assert wrong_doctor_create.status_code == 403

        created = await doctor_client.post(
            "/api/v1/medical-records",
            json=medical_payload,
            headers=_csrf_headers(doctor_client),
        )
        assert created.status_code == 201, created.text
        record_id = created.json()["id"]
        updated_note = "Updated synthetic clinical note Phase 6"
        updated = await doctor_client.patch(
            f"/api/v1/medical-records/{record_id}",
            json={"clinical_notes": updated_note},
            headers=_csrf_headers(doctor_client),
        )
        assert updated.status_code == 200
        assert updated.json()["clinical_notes"] == updated_note
        duplicate = await doctor_client.post(
            "/api/v1/medical-records",
            json=medical_payload,
            headers=_csrf_headers(doctor_client),
        )
        assert duplicate.status_code == 409

        history = await patient_client.get("/api/v1/medical-records/me/history")
        own_record = await patient_client.get(f"/api/v1/medical-records/{record_id}")
        patient_update = await patient_client.patch(
            f"/api/v1/medical-records/{record_id}",
            json={"symptoms": "Patient must not update"},
            headers=_csrf_headers(patient_client),
        )
        assert history.status_code == own_record.status_code == 200
        assert any(item["id"] == record_id for item in history.json())
        assert patient_update.status_code == 403

        await _login(
            other_patient_client,
            phase6_data.patients[0],
            phase6_data.passwords[phase6_data.patients[0].id],
        )
        await _login(
            staff_client,
            phase6_data.staff,
            phase6_data.passwords[phase6_data.staff.id],
        )
        await _login(
            admin_client,
            phase6_data.admin,
            phase6_data.passwords[phase6_data.admin.id],
        )
        assert (
            await other_patient_client.get(f"/api/v1/medical-records/{record_id}")
        ).status_code == 403
        assert (
            await staff_client.get(f"/api/v1/medical-records/{record_id}")
        ).status_code == 403
        assert (
            await admin_client.get(f"/api/v1/medical-records/{record_id}")
        ).status_code == 403

    with Session(real_database) as session:
        appointment = session.get(Appointment, UUID(appointment_id))
        slot = session.get(ScheduleSlot, phase6_data.slots[7].id)
        record = session.get(MedicalRecord, UUID(record_id))
        audits = list(
            session.scalars(
                select(AuditLog).where(
                    AuditLog.entity_type == "medical_record",
                    AuditLog.entity_id == UUID(record_id),
                )
            )
        )
        assert appointment is not None and appointment.patient_id == patient_id
        assert appointment.status == AppointmentStatus.COMPLETED
        assert slot is not None and slot.status == SlotStatus.BOOKED
        assert record is not None and record.appointment_id == appointment.id
        assert {audit.action for audit in audits} == {
            "MEDICAL_RECORD_CREATED",
            "MEDICAL_RECORD_UPDATED",
        }
        serialized_audit = json.dumps(
            [audit.audit_metadata for audit in audits], ensure_ascii=False
        )
        for clinical_value in medical_payload.values():
            if clinical_value != appointment_id:
                assert clinical_value not in serialized_audit
        assert updated_note not in serialized_audit
