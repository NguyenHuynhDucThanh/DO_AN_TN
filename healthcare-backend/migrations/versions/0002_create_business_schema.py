"""Create Phase 2 business schema and pgvector knowledge storage.

Revision ID: 0002_create_business_schema
Revises: 0001_enable_pgvector
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "0002_create_business_schema"
down_revision = "0001_enable_pgvector"
branch_labels = None
depends_on = None


def uuid_column(name: str = "id", *, primary_key: bool = False, nullable: bool = False) -> sa.Column:
    return sa.Column(
        name,
        postgresql.UUID(as_uuid=True),
        primary_key=primary_key,
        nullable=nullable,
        server_default=sa.text("gen_random_uuid()") if primary_key else None,
    )


def timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "users",
        uuid_column(primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("phone", sa.String(20)),
        sa.Column("date_of_birth", sa.Date()),
        sa.Column("gender", sa.Enum("FEMALE", "MALE", "OTHER", "UNDISCLOSED", name="gender", native_enum=False, length=16)),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "INACTIVE", "LOCKED", name="user_status", native_enum=False, length=16),
            server_default=sa.text("'ACTIVE'"), nullable=False,
        ),
        *timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("uq_users_email_ci", "users", [sa.text("lower(email)")], unique=True)

    op.create_table(
        "roles",
        uuid_column(primary_key=True),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("description", sa.String(255)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_roles"),
        sa.UniqueConstraint("code", name="uq_roles_code"),
    )
    op.create_table(
        "user_roles",
        uuid_column("user_id"),
        uuid_column("role_id"),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        uuid_column("assigned_by", nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_user_roles_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], name="fk_user_roles_role_id_roles", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], name="fk_user_roles_assigned_by_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("user_id", "role_id", name="pk_user_roles"),
    )
    op.create_table(
        "refresh_sessions",
        uuid_column(primary_key=True),
        uuid_column("user_id"),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        uuid_column("replaced_by_session_id", nullable=True),
        sa.Column("user_agent", sa.String(500)),
        sa.Column("ip_address", sa.String(45)),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_refresh_sessions_user_id_users", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["replaced_by_session_id"], ["refresh_sessions.id"], name="fk_refresh_sessions_replaced_by_session_id_refresh_sessions", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_sessions"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_sessions_token_hash"),
    )
    op.create_index("ix_refresh_sessions_user_id", "refresh_sessions", ["user_id"])
    op.create_index("ix_refresh_sessions_family_id", "refresh_sessions", ["family_id"])

    op.create_table(
        "specialties",
        uuid_column(primary_key=True),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_specialties"),
        sa.UniqueConstraint("code", name="uq_specialties_code"),
        sa.UniqueConstraint("name", name="uq_specialties_name"),
    )
    op.create_table(
        "doctors",
        uuid_column(primary_key=True),
        uuid_column("user_id"),
        uuid_column("specialty_id"),
        sa.Column("license_number", sa.String(50), nullable=False),
        sa.Column("biography", sa.Text()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_doctors_user_id_users", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["specialty_id"], ["specialties.id"], name="fk_doctors_specialty_id_specialties", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_doctors"),
        sa.UniqueConstraint("user_id", name="uq_doctors_user_id"),
        sa.UniqueConstraint("license_number", name="uq_doctors_license_number"),
    )
    op.create_index("ix_doctors_specialty_id", "doctors", ["specialty_id"])
    op.create_table(
        "doctor_schedules",
        uuid_column(primary_key=True),
        uuid_column("doctor_id"),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("slot_duration_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "CANCELLED", name="schedule_status", native_enum=False, length=16),
            server_default=sa.text("'ACTIVE'"), nullable=False,
        ),
        *timestamps(),
        sa.CheckConstraint("end_at > start_at", name="ck_doctor_schedules_valid_time_range"),
        sa.CheckConstraint("slot_duration_minutes BETWEEN 5 AND 480", name="ck_doctor_schedules_valid_slot_duration"),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], name="fk_doctor_schedules_doctor_id_doctors", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_doctor_schedules"),
        sa.UniqueConstraint("doctor_id", "start_at", "end_at", name="uq_doctor_schedules_doctor_range"),
    )
    op.create_index("ix_doctor_schedules_doctor_id", "doctor_schedules", ["doctor_id"])
    op.create_table(
        "schedule_slots",
        uuid_column(primary_key=True),
        uuid_column("schedule_id"),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum("AVAILABLE", "BOOKED", "BLOCKED", name="slot_status", native_enum=False, length=16),
            server_default=sa.text("'AVAILABLE'"), nullable=False,
        ),
        *timestamps(),
        sa.CheckConstraint("end_at > start_at", name="ck_schedule_slots_valid_time_range"),
        sa.ForeignKeyConstraint(["schedule_id"], ["doctor_schedules.id"], name="fk_schedule_slots_schedule_id_doctor_schedules", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_schedule_slots"),
        sa.UniqueConstraint("schedule_id", "start_at", name="uq_schedule_slots_schedule_start"),
    )
    op.create_index("ix_schedule_slots_schedule_id", "schedule_slots", ["schedule_id"])
    op.create_table(
        "appointments",
        uuid_column(primary_key=True),
        uuid_column("patient_id"),
        uuid_column("schedule_slot_id"),
        sa.Column(
            "status",
            sa.Enum("CONFIRMED", "CANCELLED", "COMPLETED", "NO_SHOW", name="appointment_status", native_enum=False, length=16),
            server_default=sa.text("'CONFIRMED'"), nullable=False,
        ),
        sa.Column("booked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        uuid_column("cancelled_by", nullable=True),
        sa.Column("cancellation_reason", sa.String(500)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("no_show_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.CheckConstraint("(status <> 'CANCELLED') OR cancelled_at IS NOT NULL", name="ck_appointments_cancelled_has_timestamp"),
        sa.CheckConstraint("(status <> 'COMPLETED') OR completed_at IS NOT NULL", name="ck_appointments_completed_has_timestamp"),
        sa.CheckConstraint("(status <> 'NO_SHOW') OR no_show_at IS NOT NULL", name="ck_appointments_no_show_has_timestamp"),
        sa.ForeignKeyConstraint(["patient_id"], ["users.id"], name="fk_appointments_patient_id_users", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["schedule_slot_id"], ["schedule_slots.id"], name="fk_appointments_schedule_slot_id_schedule_slots", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cancelled_by"], ["users.id"], name="fk_appointments_cancelled_by_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_appointments"),
    )
    op.create_index("ix_appointments_patient_id", "appointments", ["patient_id"])
    op.create_index("ix_appointments_schedule_slot_id", "appointments", ["schedule_slot_id"])
    op.create_index(
        "uq_appointments_active_slot", "appointments", ["schedule_slot_id"], unique=True,
        postgresql_where=sa.text("status = 'CONFIRMED'"),
    )
    op.create_table(
        "medical_records",
        uuid_column(primary_key=True),
        uuid_column("appointment_id"),
        sa.Column("symptoms", sa.Text(), nullable=False),
        sa.Column("clinical_notes", sa.Text(), nullable=False),
        sa.Column("doctor_conclusion", sa.Text(), nullable=False),
        sa.Column("follow_up_instructions", sa.Text(), nullable=False),
        uuid_column("created_by"),
        uuid_column("updated_by"),
        *timestamps(),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"], name="fk_medical_records_appointment_id_appointments", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_medical_records_created_by_users", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], name="fk_medical_records_updated_by_users", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_medical_records"),
        sa.UniqueConstraint("appointment_id", name="uq_medical_records_appointment_id"),
    )

    op.create_table(
        "documents",
        uuid_column(primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("source_name", sa.String(255)),
        sa.Column("source_url", sa.String(1000)),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("version_number", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "approval_status",
            sa.Enum("PENDING", "APPROVED", "REJECTED", name="approval_status", native_enum=False, length=16),
            server_default=sa.text("'PENDING'"), nullable=False,
        ),
        sa.Column(
            "ingestion_status",
            sa.Enum("NOT_INGESTED", "PROCESSING", "COMPLETED", "FAILED", name="ingestion_status", native_enum=False, length=20),
            server_default=sa.text("'NOT_INGESTED'"), nullable=False,
        ),
        uuid_column("uploaded_by"),
        uuid_column("approved_by", nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("ingestion_error", sa.String(1000)),
        *timestamps(),
        sa.CheckConstraint("version_number > 0", name="ck_documents_positive_version"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], name="fk_documents_uploaded_by_users", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], name="fk_documents_approved_by_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
        sa.UniqueConstraint("checksum_sha256", "version_number", name="uq_documents_checksum_version"),
    )
    op.create_table(
        "document_chunks",
        uuid_column(primary_key=True),
        uuid_column("document_id"),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=False),
        sa.Column("page_number", sa.Integer()),
        sa.Column("section", sa.String(255)),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("chunk_index >= 0", name="ck_document_chunks_non_negative_chunk_index"),
        sa.CheckConstraint("page_number IS NULL OR page_number > 0", name="ck_document_chunks_positive_page_number"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], name="fk_document_chunks_document_id_documents", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_document_chunks"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunks_document_index"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index(
        "ix_document_chunks_embedding_hnsw", "document_chunks", ["embedding"],
        postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "handoff_requests",
        uuid_column(primary_key=True),
        uuid_column("requester_id"),
        uuid_column("assigned_to", nullable=True),
        sa.Column("source", sa.String(30), server_default=sa.text("'CHATBOT'"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "priority",
            sa.Enum("NORMAL", "HIGH", "URGENT", name="handoff_priority", native_enum=False, length=16),
            server_default=sa.text("'NORMAL'"), nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("PENDING", "IN_PROGRESS", "RESOLVED", "CANCELLED", name="handoff_status", native_enum=False, length=16),
            server_default=sa.text("'PENDING'"), nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        *timestamps(),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], name="fk_handoff_requests_requester_id_users", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], name="fk_handoff_requests_assigned_to_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_handoff_requests"),
    )
    op.create_index("ix_handoff_requests_requester_id", "handoff_requests", ["requester_id"])
    op.create_index("ix_handoff_requests_assigned_to", "handoff_requests", ["assigned_to"])
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        uuid_column("actor_user_id", nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False),
        uuid_column("entity_id", nullable=True),
        uuid_column("request_id", nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], name="fk_audit_logs_actor_user_id_users", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_logs_occurred_at", "audit_logs", ["occurred_at"])


def downgrade() -> None:
    for table_name in (
        "audit_logs", "handoff_requests", "document_chunks", "documents", "medical_records",
        "appointments", "schedule_slots", "doctor_schedules", "doctors", "specialties",
        "refresh_sessions", "user_roles", "roles", "users",
    ):
        op.drop_table(table_name)
