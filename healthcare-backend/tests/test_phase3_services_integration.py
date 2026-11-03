"""Phase 3 business-service integration tests against PostgreSQL."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.appointments.schemas import AppointmentCancel, AppointmentCreate
from app.appointments.service import AppointmentService
from app.auth.context import ActorContext
from app.auth.dependencies import get_current_actor
from app.core.database import get_db
from app.core.errors import BadRequestError, ConflictError, ForbiddenError
from app.doctors.schemas import DoctorCreate, DoctorUpdate
from app.doctors.service import DoctorService
from app.documents.schemas import DocumentCreate, DocumentReview
from app.documents.service import DocumentService
from app.handoffs.schemas import HandoffCreate, HandoffUpdate
from app.handoffs.service import HandoffService
from app.medical_records.schemas import MedicalRecordCreate, MedicalRecordUpdate
from app.medical_records.service import MedicalRecordService
from app.models.care import Appointment, Doctor, DoctorSchedule, ScheduleSlot
from app.models.enums import (
    ApprovalStatus,
    AppointmentStatus,
    HandoffPriority,
    HandoffStatus,
    ScheduleStatus,
    SlotStatus,
    UserStatus,
)
from app.models.identity import Role, User, UserRole
from app.models.medical_record import MedicalRecord
from app.models.operations import AuditLog
from app.schedules.schemas import ScheduleCreate, SlotStatusUpdate
from app.schedules.service import ScheduleService
from app.specialties.schemas import SpecialtyCreate, SpecialtyStatusUpdate, SpecialtyUpdate
from app.specialties.service import SpecialtyService
from app.main import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
def phase3_session(real_database):
    connection = real_database.connect()
    outer_transaction = connection.begin()
    session = Session(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


def actor_for_email(session: Session, email: str) -> ActorContext:
    user = session.scalar(select(User).where(User.email == email))
    assert user is not None
    roles = frozenset(
        session.scalars(
            select(Role.code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user.id)
        ).all()
    )
    return ActorContext(user.id, roles)


def create_user_with_role(session: Session, role_code: str, prefix: str) -> User:
    role = session.scalar(select(Role).where(Role.code == role_code))
    assert role is not None
    user = User(
        email=f"{prefix}.{uuid4().hex[:10]}@example.invalid",
        password_hash="!phase5-auth-not-configured",
        full_name=f"{prefix} Synthetic",
        phone="0900000099",
        status=UserStatus.ACTIVE,
    )
    session.add(user)
    session.flush()
    session.add(UserRole(user_id=user.id, role_id=role.id))
    session.commit()
    return user


@pytest.fixture
def actors(phase3_session: Session) -> dict[str, ActorContext]:
    admin = create_user_with_role(phase3_session, "ADMIN", "admin")
    return {
        "admin": ActorContext(admin.id, frozenset({"ADMIN"})),
        "doctor": actor_for_email(phase3_session, "doctor.an@example.invalid"),
        "patient": actor_for_email(phase3_session, "patient.lan@example.invalid"),
        "staff": actor_for_email(phase3_session, "staff.demo@example.invalid"),
    }


def seeded_doctor(session: Session) -> Doctor:
    doctor = session.scalar(select(Doctor).join(Doctor.user).where(User.email == "doctor.an@example.invalid"))
    assert doctor is not None
    return doctor


def test_specialty_and_doctor_crud_with_rollback(
    phase3_session: Session, actors: dict[str, ActorContext]
) -> None:
    suffix = uuid4().hex[:8].upper()
    specialties = SpecialtyService(phase3_session)
    specialty = specialties.create(
        SpecialtyCreate(code=f"TEST_{suffix}", name=f"Chuyên khoa {suffix}", description="Synthetic"),
        actors["admin"],
    )
    assert specialties.get(specialty.id).code == f"TEST_{suffix}"
    updated = specialties.update(
        specialty.id, SpecialtyUpdate(description="Updated synthetic"), actors["admin"]
    )
    assert updated.description == "Updated synthetic"
    assert specialties.set_status(
        specialty.id, SpecialtyStatusUpdate(is_active=False), actors["admin"]
    ).is_active is False
    specialties.set_status(specialty.id, SpecialtyStatusUpdate(is_active=True), actors["admin"])

    other = specialties.create(
        SpecialtyCreate(code=f"OTHER_{suffix}", name=f"Khác {suffix}"), actors["admin"]
    )
    with pytest.raises(ConflictError):
        specialties.update(other.id, SpecialtyUpdate(name=specialty.name), actors["admin"])
    assert specialties.get(other.id).code == f"OTHER_{suffix}"

    doctor_user = create_user_with_role(phase3_session, "DOCTOR", "doctor")
    doctors = DoctorService(phase3_session)
    doctor = doctors.create(
        DoctorCreate(
            user_id=doctor_user.id,
            specialty_id=specialty.id,
            license_number=f"DEMO-{suffix}",
            biography="Synthetic doctor",
        ),
        actors["admin"],
    )
    assert doctor in doctors.list(specialty.id, True)
    assert doctors.update(
        doctor.id, DoctorUpdate(biography="Updated biography"), actors["admin"]
    ).biography == "Updated biography"


def test_schedule_validation_slot_generation_and_blocking(
    phase3_session: Session, actors: dict[str, ActorContext]
) -> None:
    doctor = seeded_doctor(phase3_session)
    service = ScheduleService(phase3_session)
    start = datetime(2031, 1, 10, 1, 0, tzinfo=timezone.utc)
    schedule = service.create(
        ScheduleCreate(
            doctor_id=doctor.id,
            start_at=start,
            end_at=start + timedelta(hours=2),
            slot_duration_minutes=30,
        ),
        actors["doctor"],
    )
    with pytest.raises(ConflictError, match="overlapping"):
        service.create(
            ScheduleCreate(
                doctor_id=doctor.id,
                start_at=start + timedelta(hours=1),
                end_at=start + timedelta(hours=3),
                slot_duration_minutes=30,
            ),
            actors["doctor"],
        )
    with pytest.raises(BadRequestError):
        service.create(
            ScheduleCreate(
                doctor_id=doctor.id,
                start_at=start + timedelta(days=1),
                end_at=start + timedelta(days=1, minutes=50),
                slot_duration_minutes=30,
            ),
            actors["doctor"],
        )
    slots = service.generate_slots(schedule.id, actors["doctor"])
    assert len(slots) == 4
    with pytest.raises(ConflictError, match="already been generated"):
        service.generate_slots(schedule.id, actors["doctor"])
    blocked = service.set_slot_status(
        slots[0].id, SlotStatusUpdate(blocked=True), actors["doctor"]
    )
    assert blocked.status == SlotStatus.BLOCKED
    available = service.available_slots(start, start + timedelta(hours=2), doctor.id)
    assert {slot.id for slot in available} == {slot.id for slot in slots[1:]}


def test_appointment_booking_cancel_rebook_and_blocked_slot(
    phase3_session: Session, actors: dict[str, ActorContext]
) -> None:
    doctor = seeded_doctor(phase3_session)
    schedules = ScheduleService(phase3_session)
    start = datetime(2031, 2, 10, 1, 0, tzinfo=timezone.utc)
    schedule = schedules.create(
        ScheduleCreate(
            doctor_id=doctor.id,
            start_at=start,
            end_at=start + timedelta(hours=1),
            slot_duration_minutes=30,
        ),
        actors["doctor"],
    )
    slots = schedules.generate_slots(schedule.id, actors["doctor"])
    schedules.set_slot_status(slots[1].id, SlotStatusUpdate(blocked=True), actors["doctor"])
    appointments = AppointmentService(phase3_session)
    booked = appointments.create(AppointmentCreate(schedule_slot_id=slots[0].id), actors["patient"])
    assert booked.status == AppointmentStatus.CONFIRMED
    with pytest.raises(ConflictError):
        appointments.create(AppointmentCreate(schedule_slot_id=slots[1].id), actors["patient"])
    cancelled = appointments.cancel(
        booked.id, AppointmentCancel(reason="Synthetic cancellation"), actors["patient"]
    )
    assert cancelled.status == AppointmentStatus.CANCELLED
    rebooked = appointments.create(AppointmentCreate(schedule_slot_id=slots[0].id), actors["patient"])
    assert rebooked.id != booked.id


def create_completed_appointment(session: Session, patient_id, doctor_id) -> Appointment:
    start = datetime(2026, 10, 18, 1, 0, tzinfo=timezone.utc)
    schedule = DoctorSchedule(
        doctor_id=doctor_id,
        start_at=start,
        end_at=start + timedelta(hours=1),
        slot_duration_minutes=30,
        status=ScheduleStatus.ACTIVE,
    )
    session.add(schedule)
    session.flush()
    slot = ScheduleSlot(
        schedule_id=schedule.id,
        start_at=start,
        end_at=start + timedelta(minutes=30),
        status=SlotStatus.BOOKED,
    )
    session.add(slot)
    session.flush()
    appointment = Appointment(
        patient_id=patient_id,
        schedule_slot_id=slot.id,
        status=AppointmentStatus.COMPLETED,
        booked_at=start - timedelta(days=1),
        completed_at=start + timedelta(minutes=25),
    )
    session.add(appointment)
    session.commit()
    return appointment


def test_medical_record_create_update_privacy_history_and_audit(
    phase3_session: Session, actors: dict[str, ActorContext]
) -> None:
    doctor = seeded_doctor(phase3_session)
    appointment = create_completed_appointment(
        phase3_session, actors["patient"].user_id, doctor.id
    )
    service = MedicalRecordService(phase3_session)
    record = service.create_medical_record(
        MedicalRecordCreate(
            appointment_id=appointment.id,
            symptoms="Synthetic symptom",
            clinical_notes="Synthetic clinical note",
            doctor_conclusion="Synthetic doctor conclusion",
            follow_up_instructions="Synthetic follow-up",
        ),
        actors["doctor"],
    )
    assert record.appointment_id == appointment.id
    with pytest.raises(ConflictError) as duplicate:
        service.create_medical_record(
            MedicalRecordCreate(
                appointment_id=appointment.id,
                symptoms="Duplicate",
                clinical_notes="Duplicate",
                doctor_conclusion="Duplicate",
                follow_up_instructions="Duplicate",
            ),
            actors["doctor"],
        )
    assert duplicate.value.status_code == 409
    updated = service.update_medical_record(
        record.id, MedicalRecordUpdate(clinical_notes="Updated synthetic note"), actors["doctor"]
    )
    assert updated.clinical_notes == "Updated synthetic note"
    assert service.get_medical_record(record.id, actors["patient"]).id == record.id
    history = service.list_patient_medical_history(actors["patient"].user_id, actors["patient"])
    assert record.id in {item.id for item in history}
    with pytest.raises(ForbiddenError):
        service.get_medical_record(record.id, actors["staff"])
    with pytest.raises(ForbiddenError):
        service.get_medical_record(record.id, actors["admin"])
    wrong_doctor = ActorContext(uuid4(), frozenset({"DOCTOR"}))
    with pytest.raises(ForbiddenError):
        service.update_medical_record(
            record.id, MedicalRecordUpdate(symptoms="Unauthorized"), wrong_doctor
        )
    audits = list(
        phase3_session.scalars(
            select(AuditLog).where(
                AuditLog.entity_type == "medical_record", AuditLog.entity_id == record.id
            )
        )
    )
    assert {audit.action for audit in audits} == {
        "MEDICAL_RECORD_CREATED",
        "MEDICAL_RECORD_UPDATED",
    }
    assert all(
        not {"symptoms", "clinical_notes", "doctor_conclusion"}.intersection(
            audit.audit_metadata.keys()
        )
        for audit in audits
    )


@pytest.mark.parametrize(
    "invalid_status",
    [
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
    ],
)
def test_medical_record_rejects_invalid_appointment_and_filters_patient(
    phase3_session: Session,
    actors: dict[str, ActorContext],
    invalid_status: AppointmentStatus,
) -> None:
    doctor = seeded_doctor(phase3_session)
    start = datetime(2031, 3, 1, 1, 0, tzinfo=timezone.utc)
    schedule = DoctorSchedule(
        doctor_id=doctor.id,
        start_at=start,
        end_at=start + timedelta(hours=1),
        slot_duration_minutes=30,
        status=ScheduleStatus.ACTIVE,
    )
    phase3_session.add(schedule)
    phase3_session.flush()
    slot = ScheduleSlot(
        schedule_id=schedule.id,
        start_at=start,
        end_at=start + timedelta(minutes=30),
        status=SlotStatus.BOOKED,
    )
    phase3_session.add(slot)
    phase3_session.flush()
    terminal_at = datetime.now(timezone.utc)
    appointment = Appointment(
        patient_id=actors["patient"].user_id,
        schedule_slot_id=slot.id,
        status=invalid_status,
        booked_at=datetime.now(timezone.utc),
        cancelled_at=terminal_at if invalid_status == AppointmentStatus.CANCELLED else None,
        cancelled_by=(
            actors["patient"].user_id
            if invalid_status == AppointmentStatus.CANCELLED
            else None
        ),
        cancellation_reason=(
            "Synthetic cancellation"
            if invalid_status == AppointmentStatus.CANCELLED
            else None
        ),
        no_show_at=terminal_at if invalid_status == AppointmentStatus.NO_SHOW else None,
    )
    phase3_session.add(appointment)
    phase3_session.commit()
    service = MedicalRecordService(phase3_session)
    with pytest.raises(ConflictError) as invalid_state:
        service.create_medical_record(
            MedicalRecordCreate(
                appointment_id=appointment.id,
                symptoms="Synthetic",
                clinical_notes="Synthetic",
                doctor_conclusion="Synthetic",
                follow_up_instructions="Synthetic",
            ),
            actors["doctor"],
        )
    assert invalid_state.value.code == "appointment_not_completed"
    assert phase3_session.scalar(
        select(MedicalRecord).where(MedicalRecord.appointment_id == appointment.id)
    ) is None
    with pytest.raises(ForbiddenError):
        service.list_patient_medical_history(
            actors["patient"].user_id,
            ActorContext(uuid4(), frozenset({"PATIENT"})),
        )


def test_document_metadata_and_handoff_workflows(
    phase3_session: Session, actors: dict[str, ActorContext]
) -> None:
    documents = DocumentService(phase3_session)
    document = documents.create(
        DocumentCreate(
            title="Synthetic medical source",
            file_name="synthetic.pdf",
            file_type="PDF",
            storage_key=f"test/{uuid4()}.pdf",
            checksum_sha256=uuid4().hex + uuid4().hex,
        ),
        actors["staff"],
    )
    reviewed = documents.review(
        document.id,
        DocumentReview(approval_status=ApprovalStatus.APPROVED),
        actors["admin"],
    )
    assert reviewed.approval_status == ApprovalStatus.APPROVED
    assert reviewed.ingestion_status.value == "NOT_INGESTED"

    disposable = documents.create(
        DocumentCreate(
            title="Disposable synthetic metadata",
            file_name="disposable.pdf",
            file_type="PDF",
            storage_key=f"test/{uuid4()}.pdf",
            checksum_sha256=uuid4().hex + uuid4().hex,
        ),
        actors["staff"],
    )
    documents.delete(disposable.id, actors["admin"])
    assert phase3_session.get(type(disposable), disposable.id) is None
    with pytest.raises(ConflictError):
        documents.delete(reviewed.id, actors["admin"])

    handoffs = HandoffService(phase3_session)
    handoff = handoffs.create(
        HandoffCreate(reason="Need synthetic human support", priority=HandoffPriority.HIGH),
        actors["patient"],
    )
    assert handoff.priority == HandoffPriority.NORMAL
    in_progress = handoffs.update(
        handoff.id,
        HandoffUpdate(assigned_to=actors["staff"].user_id, status=HandoffStatus.IN_PROGRESS),
        actors["staff"],
    )
    assert in_progress.assigned_to == actors["staff"].user_id
    resolved = handoffs.update(
        handoff.id,
        HandoffUpdate(status=HandoffStatus.RESOLVED),
        actors["staff"],
    )
    assert resolved.resolved_at is not None


@pytest.mark.anyio
async def test_specialty_router_and_conflict_error_contract(
    phase3_session: Session, actors: dict[str, ActorContext]
) -> None:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: phase3_session
    app.dependency_overrides[get_current_actor] = lambda: actors["admin"]
    suffix = uuid4().hex[:8].upper()
    payload = {"code": f"API_{suffix}", "name": f"API Specialty {suffix}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        created = await client.post("/api/v1/specialties", json=payload)
        duplicate = await client.post("/api/v1/specialties", json=payload)
        missing = await client.get(f"/api/v1/specialties/{uuid4()}")
        invalid = await client.post("/api/v1/specialties", json={"code": "X", "name": ""})
        invalid_range = await client.get(
            "/api/v1/schedules/available-slots",
            params={
                "from_at": "2031-01-02T00:00:00+00:00",
                "to_at": "2031-01-01T00:00:00+00:00",
            },
        )
    assert created.status_code == 201
    assert created.json()["code"] == payload["code"]
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "specialty_exists"
    assert missing.status_code == 404
    assert invalid.status_code == 422
    assert invalid_range.status_code == 400
    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_dev_actor_uses_database_roles_and_protects_clinical_data(
    phase3_session: Session, actors: dict[str, ActorContext]
) -> None:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: phase3_session
    record_id = phase3_session.scalar(select(MedicalRecord.id).limit(1))
    assert record_id is not None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        patient_history = await client.get(
            "/api/v1/medical-records/me/history",
            headers={"X-Dev-User-Id": str(actors["patient"].user_id)},
        )
        staff_read = await client.get(
            f"/api/v1/medical-records/{record_id}",
            headers={"X-Dev-User-Id": str(actors["staff"].user_id)},
        )
    assert patient_history.status_code == 200
    assert staff_read.status_code == 403
    app.dependency_overrides.clear()
