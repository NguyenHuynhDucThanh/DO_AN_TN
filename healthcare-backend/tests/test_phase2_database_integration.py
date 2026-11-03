"""Phase 2 constraints, pgvector storage, rollback, and seed checks."""

from uuid import uuid4

import pytest
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Appointment, Document, DocumentChunk, MedicalRecord, Role, User
from app.models.enums import ApprovalStatus, AppointmentStatus

pytestmark = pytest.mark.integration


def test_seed_is_consistent_and_medical_record_uses_completed_appointment(real_database: Engine) -> None:
    with Session(real_database) as session:
        assert {role.code for role in session.scalars(select(Role))} >= {"PATIENT", "DOCTOR", "STAFF", "ADMIN"}
        record = session.scalar(select(MedicalRecord).join(Appointment).where(Appointment.status == AppointmentStatus.COMPLETED))
        assert record is not None
        assert record.appointment.status == AppointmentStatus.COMPLETED
        assert session.scalar(select(MedicalRecord).where(MedicalRecord.appointment_id == record.appointment_id)) is record


def test_medical_record_cannot_be_orphaned(real_database: Engine) -> None:
    with real_database.connect() as connection:
        transaction = connection.begin()
        actor_id = connection.execute(text("SELECT id FROM users ORDER BY email LIMIT 1")).scalar_one()
        with pytest.raises(IntegrityError) as exc_info:
            connection.execute(
                text(
                    "INSERT INTO medical_records "
                    "(appointment_id, symptoms, clinical_notes, doctor_conclusion, follow_up_instructions, created_by, updated_by) "
                    "VALUES (:appointment_id, 'demo', 'demo', 'demo', 'demo', :actor_id, :actor_id)"
                ),
                {"appointment_id": uuid4(), "actor_id": actor_id},
            )
        assert exc_info.value.orig.diag.constraint_name == "fk_medical_records_appointment_id_appointments"
        transaction.rollback()


def test_one_medical_record_per_appointment(real_database: Engine) -> None:
    with real_database.connect() as connection:
        transaction = connection.begin()
        row = connection.execute(
            text("SELECT appointment_id, created_by FROM medical_records LIMIT 1")
        ).mappings().one()
        with pytest.raises(IntegrityError) as exc_info:
            connection.execute(
                text(
                    "INSERT INTO medical_records "
                    "(appointment_id, symptoms, clinical_notes, doctor_conclusion, follow_up_instructions, created_by, updated_by) "
                    "VALUES (:appointment_id, 'demo', 'demo', 'demo', 'demo', :actor_id, :actor_id)"
                ),
                {"appointment_id": row["appointment_id"], "actor_id": row["created_by"]},
            )
        assert exc_info.value.orig.diag.constraint_name == "uq_medical_records_appointment_id"
        transaction.rollback()


def test_confirmed_appointment_prevents_double_booking(real_database: Engine) -> None:
    with real_database.connect() as connection:
        transaction = connection.begin()
        row = connection.execute(
            text(
                "SELECT a.patient_id, a.schedule_slot_id FROM appointments a "
                "WHERE a.status = 'CONFIRMED' LIMIT 1"
            )
        ).mappings().one()
        with pytest.raises(IntegrityError) as exc_info:
            connection.execute(
                text(
                    "INSERT INTO appointments (patient_id, schedule_slot_id, status, booked_at) "
                    "VALUES (:patient_id, :slot_id, 'CONFIRMED', now())"
                ),
                {"patient_id": row["patient_id"], "slot_id": row["schedule_slot_id"]},
            )
        assert exc_info.value.orig.diag.constraint_name == "uq_appointments_occupied_slot"
        transaction.rollback()


def test_terminal_appointment_keeps_slot_occupied(real_database: Engine) -> None:
    with real_database.connect() as connection:
        transaction = connection.begin()
        row = connection.execute(
            text(
                "SELECT patient_id, schedule_slot_id FROM appointments "
                "WHERE status = 'COMPLETED' LIMIT 1"
            )
        ).mappings().one()
        with pytest.raises(IntegrityError) as exc_info:
            connection.execute(
                text(
                    "INSERT INTO appointments (patient_id, schedule_slot_id, status, booked_at) "
                    "VALUES (:patient_id, :slot_id, 'CONFIRMED', now())"
                ),
                {"patient_id": row["patient_id"], "slot_id": row["schedule_slot_id"]},
            )
        assert exc_info.value.orig.diag.constraint_name == "uq_appointments_occupied_slot"
        transaction.rollback()


def test_cancelled_appointment_allows_slot_rebooking(real_database: Engine) -> None:
    with real_database.connect() as connection:
        transaction = connection.begin()
        row = connection.execute(
            text(
                "SELECT ds.id AS schedule_id, a.patient_id "
                "FROM doctor_schedules ds CROSS JOIN appointments a "
                "WHERE ds.start_at = '2030-01-15 01:00:00+00'::timestamptz LIMIT 1"
            )
        ).mappings().one()
        slot_id = connection.execute(
            text(
                "INSERT INTO schedule_slots (schedule_id, start_at, end_at, status) "
                "VALUES (:schedule_id, '2030-01-15 02:00:00+00', '2030-01-15 02:30:00+00', 'BOOKED') "
                "RETURNING id"
            ),
            {"schedule_id": row["schedule_id"]},
        ).scalar_one()
        connection.execute(
            text(
                "INSERT INTO appointments (patient_id, schedule_slot_id, status, booked_at, cancelled_at) "
                "VALUES (:patient_id, :slot_id, 'CANCELLED', now(), now())"
            ),
            {"patient_id": row["patient_id"], "slot_id": slot_id},
        )
        connection.execute(
            text(
                "INSERT INTO appointments (patient_id, schedule_slot_id, status, booked_at) "
                "VALUES (:patient_id, :slot_id, 'CONFIRMED', now())"
            ),
            {"patient_id": row["patient_id"], "slot_id": slot_id},
        )
        assert connection.execute(
            text("SELECT count(*) FROM appointments WHERE schedule_slot_id=:slot_id"), {"slot_id": slot_id}
        ).scalar_one() == 2
        transaction.rollback()


def test_handoff_rejects_status_outside_srs(real_database: Engine) -> None:
    with real_database.connect() as connection:
        transaction = connection.begin()
        requester_id = connection.execute(text("SELECT id FROM users ORDER BY email LIMIT 1")).scalar_one()
        with pytest.raises(IntegrityError) as exc_info:
            connection.execute(
                text(
                    "INSERT INTO handoff_requests (requester_id, reason, status) "
                    "VALUES (:requester_id, 'Synthetic test', 'CANCELLED')"
                ),
                {"requester_id": requester_id},
            )
        assert exc_info.value.orig.diag.constraint_name == "ck_handoff_requests_handoff_status"
        transaction.rollback()


def test_vector_1024_insert_and_cosine_search(real_database: Engine) -> None:
    with real_database.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection) as session:
            uploader = session.scalar(select(User).order_by(User.email))
            assert uploader is not None
            document = Document(
                title="Tài liệu vector tạm thời",
                file_name="temporary.pdf",
                file_type="PDF",
                storage_key="test/temporary.pdf",
                checksum_sha256="f" * 64,
                approval_status=ApprovalStatus.APPROVED,
                uploaded_by=uploader.id,
            )
            embedding = [1.0] + [0.0] * 1023
            document.chunks.append(
                DocumentChunk(chunk_index=0, content="Nội dung kiểm thử.", embedding=embedding, content_hash="e" * 64)
            )
            session.add(document)
            session.flush()
            distance = session.scalar(
                select(DocumentChunk.embedding.cosine_distance(embedding)).where(DocumentChunk.document_id == document.id)
            )
            assert distance == pytest.approx(0.0)
        transaction.rollback()


def test_transaction_rollback_leaves_no_row(real_database: Engine) -> None:
    code = f"RB_{uuid4().hex[:12]}"
    with real_database.connect() as connection:
        transaction = connection.begin()
        connection.execute(
            text("INSERT INTO roles (code, name) VALUES (:code, 'Rollback test')"), {"code": code}
        )
        transaction.rollback()
    with real_database.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM roles WHERE code=:code"), {"code": code}).scalar_one() == 0
