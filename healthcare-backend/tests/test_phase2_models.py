"""Fast metadata checks that do not require a live database."""

from app.core.database import Base
from app.models import EMBEDDING_DIMENSION  # imports/registers all models


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
