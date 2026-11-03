"""Enable pgvector infrastructure without creating a business schema.

Revision ID: 0001_enable_pgvector
Revises: None
"""

from alembic import op

revision = "0001_enable_pgvector"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # bootstrap_database.py enables this as an administrator first. IF NOT EXISTS
    # also supports a database owner who has already installed the extension.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    # Do not drop a shared extension or cascade-delete future vector data.
    # Downgrading this foundation revision only removes the Alembic version marker.
    pass
