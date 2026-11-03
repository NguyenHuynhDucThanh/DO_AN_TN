"""Strengthen terminal-slot and persisted enum invariants after final audit.

Revision ID: 0003_phase2_invariants
Revises: 0002_create_business_schema
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_phase2_invariants"
down_revision = "0002_create_business_schema"
branch_labels = None
depends_on = None


ENUM_CHECKS = (
    ("users", "gender", "gender IN ('FEMALE', 'MALE', 'OTHER', 'UNDISCLOSED')"),
    ("users", "user_status", "status IN ('ACTIVE', 'INACTIVE', 'LOCKED')"),
    ("doctor_schedules", "schedule_status", "status IN ('ACTIVE', 'CANCELLED')"),
    ("schedule_slots", "slot_status", "status IN ('AVAILABLE', 'BOOKED', 'BLOCKED')"),
    (
        "appointments",
        "appointment_status",
        "status IN ('CONFIRMED', 'CANCELLED', 'COMPLETED', 'NO_SHOW')",
    ),
    ("documents", "approval_status", "approval_status IN ('PENDING', 'APPROVED', 'REJECTED')"),
    (
        "documents",
        "ingestion_status",
        "ingestion_status IN ('NOT_INGESTED', 'PROCESSING', 'COMPLETED', 'FAILED')",
    ),
    ("handoff_requests", "handoff_priority", "priority IN ('NORMAL', 'HIGH', 'URGENT')"),
    (
        "handoff_requests",
        "handoff_status",
        "status IN ('PENDING', 'IN_PROGRESS', 'RESOLVED')",
    ),
)


def upgrade() -> None:
    op.drop_index("uq_appointments_active_slot", table_name="appointments")
    op.create_index(
        "uq_appointments_occupied_slot",
        "appointments",
        ["schedule_slot_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('CONFIRMED', 'COMPLETED', 'NO_SHOW')"),
    )

    for table_name, constraint_name, condition in ENUM_CHECKS:
        op.create_check_constraint(constraint_name, table_name, condition)

    op.create_check_constraint(
        "supported_file_type",
        "documents",
        "file_type IN ('CSV', 'PDF', 'DOCX')",
    )
    op.create_check_constraint(
        "ingestion_requires_approval",
        "documents",
        "ingestion_status = 'NOT_INGESTED' OR approval_status = 'APPROVED'",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_documents_ingestion_requires_approval"), "documents", type_="check")
    op.drop_constraint(op.f("ck_documents_supported_file_type"), "documents", type_="check")
    for table_name, constraint_name, _ in reversed(ENUM_CHECKS):
        op.drop_constraint(op.f(f"ck_{table_name}_{constraint_name}"), table_name, type_="check")

    op.drop_index("uq_appointments_occupied_slot", table_name="appointments")
    op.create_index(
        "uq_appointments_active_slot",
        "appointments",
        ["schedule_slot_id"],
        unique=True,
        postgresql_where=sa.text("status = 'CONFIRMED'"),
    )
