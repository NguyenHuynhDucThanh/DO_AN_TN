"""Allow JSON as a governed RAG document source.

Revision ID: 0004_add_json_document_type
Revises: 0003_phase2_invariants
"""

from alembic import op

revision = "0004_add_json_document_type"
down_revision = "0003_phase2_invariants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_documents_supported_file_type"), "documents", type_="check")
    op.create_check_constraint(
        "supported_file_type",
        "documents",
        "file_type IN ('JSON', 'CSV', 'PDF', 'DOCX')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_documents_supported_file_type"), "documents", type_="check")
    op.create_check_constraint(
        "supported_file_type",
        "documents",
        "file_type IN ('CSV', 'PDF', 'DOCX')",
    )
