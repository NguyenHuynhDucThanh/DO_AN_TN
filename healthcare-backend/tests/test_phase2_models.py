"""Fast metadata checks that do not require a live database."""

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

from app.core.database import Base
from app.appointments.schemas import AppointmentRead
from app.models import EMBEDDING_DIMENSION  # imports/registers all models
from app.models.enums import AppointmentStatus, SlotStatus
from app.schedules.schemas import AvailableSlotRead


def test_phase2_metadata_has_expected_tables() -> None:
    assert set(Base.metadata.tables) == {
        "appointments", "audit_logs", "doctor_schedules", "doctors", "document_chunks",
        "documents", "handoff_requests", "medical_records", "refresh_sessions", "roles",
        "schedule_slots", "specialties", "user_roles", "users",
    }


def test_bge_m3_dimension_and_medical_record_cardinality() -> None:
    assert EMBEDDING_DIMENSION == 1024
    table = Base.metadata.tables["medical_records"]
    assert table.c.appointment_id.foreign_keys
    assert any(
        constraint.name == "uq_medical_records_appointment_id"
        for constraint in table.constraints
    )


def test_occupied_appointment_partial_unique_index_exists() -> None:
    indexes = {index.name: index for index in Base.metadata.tables["appointments"].indexes}
    index = indexes["uq_appointments_occupied_slot"]
    assert index.unique is True
    assert str(index.dialect_options["postgresql"]["where"]) == "status IN ('CONFIRMED', 'COMPLETED', 'NO_SHOW')"


def test_available_slot_projection_includes_doctor_and_specialty_context() -> None:
    now = datetime.now(timezone.utc)
    doctor_id = uuid4()
    specialty_id = uuid4()
    slot = SimpleNamespace(
        id=uuid4(),
        schedule_id=uuid4(),
        start_at=now,
        end_at=now,
        status=SlotStatus.AVAILABLE,
        created_at=now,
        updated_at=now,
        schedule=SimpleNamespace(doctor=SimpleNamespace(
            id=doctor_id,
            user=SimpleNamespace(full_name="BS. Nguyễn Minh An"),
            specialty=SimpleNamespace(id=specialty_id, name="Nội tổng quát"),
        )),
    )

    projection = AvailableSlotRead.model_validate(slot)

    assert projection.doctor_id == doctor_id
    assert projection.doctor_name == "BS. Nguyễn Minh An"
    assert projection.specialty_id == specialty_id
    assert projection.specialty_name == "Nội tổng quát"


def test_appointment_projection_has_short_reference_and_human_context() -> None:
    now = datetime.now(timezone.utc)
    appointment_id = UUID("8a7d5e07-6656-4ac4-884c-639444b03fd2")
    slot = SimpleNamespace(
        id=uuid4(),
        start_at=now,
        end_at=now,
        schedule=SimpleNamespace(doctor=SimpleNamespace(
            id=uuid4(),
            user=SimpleNamespace(full_name="BS. Nguyễn Minh An"),
            specialty=SimpleNamespace(id=uuid4(), name="Nội tổng quát"),
        )),
    )
    appointment = SimpleNamespace(
        id=appointment_id,
        patient_id=uuid4(),
        patient=SimpleNamespace(full_name="Nguyễn Văn Bệnh nhân"),
        schedule_slot_id=slot.id,
        schedule_slot=slot,
        status=AppointmentStatus.CONFIRMED,
        booked_at=now,
        cancelled_at=None,
        cancelled_by=None,
        cancellation_reason=None,
        completed_at=None,
        no_show_at=None,
        created_at=now,
        updated_at=now,
    )

    projection = AppointmentRead.model_validate(appointment)

    assert projection.reference_code == "LH-8A7D5E07"
    assert projection.doctor_name == "BS. Nguyễn Minh An"
    assert projection.specialty_name == "Nội tổng quát"
    assert projection.patient_name == "Nguyễn Văn Bệnh nhân"
