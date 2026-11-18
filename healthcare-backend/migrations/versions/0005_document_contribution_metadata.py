"""Add governed Doctor contribution metadata and checksum guard.

Revision ID: 0005_document_contribution
Revises: 0004_add_json_document_type
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0005_document_contribution"
down_revision: str | None = "0004_add_json_document_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("rejection_reason", sa.String(1000), nullable=True))
    op.add_column("documents", sa.Column("mime_type", sa.String(150), nullable=True))
    op.add_column("documents", sa.Column("file_size_bytes", sa.BigInteger(), nullable=True))
    op.add_column("documents", sa.Column("author_name", sa.String(255), nullable=True))
    op.add_column("documents", sa.Column("organization", sa.String(255), nullable=True))
    op.add_column("documents", sa.Column("publication_year", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "document_file_size_positive",
        "documents",
        "file_size_bytes IS NULL OR file_size_bytes > 0",
    )
    op.create_check_constraint(
        "document_publication_year_minimum",
        "documents",
        "publication_year IS NULL OR publication_year >= 1800",
    )
    op.drop_constraint("uq_documents_checksum_version", "documents", type_="unique")
    op.create_unique_constraint("uq_documents_checksum", "documents", ["checksum_sha256"])
    op.alter_column(
        "documents",
        "approved_by",
        comment="User who performed the latest APPROVE or REJECT review.",
    )
    op.alter_column(
        "documents",
        "approved_at",
        comment="Timestamp of the latest APPROVE or REJECT review.",
    )


def downgrade() -> None:
    op.alter_column("documents", "approved_at", comment=None)
    op.alter_column("documents", "approved_by", comment=None)
    op.drop_constraint("uq_documents_checksum", "documents", type_="unique")
    op.create_unique_constraint(
        "uq_documents_checksum_version",
        "documents",
        ["checksum_sha256", "version_number"],
    )
    op.drop_constraint(
        "ck_documents_document_publication_year_minimum", "documents", type_="check"
    )
    op.drop_constraint("ck_documents_document_file_size_positive", "documents", type_="check")
    op.drop_column("documents", "publication_year")
    op.drop_column("documents", "organization")
    op.drop_column("documents", "author_name")
    op.drop_column("documents", "file_size_bytes")
    op.drop_column("documents", "mime_type")
    op.drop_column("documents", "rejection_reason")
