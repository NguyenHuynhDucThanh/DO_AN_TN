"""Check actual SQLAlchemy connectivity, pgvector, business schema, and Alembic."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core.database import get_engine


def main() -> int:
    try:
        backend_root = Path(__file__).resolve().parents[1]
        alembic_config = Config(str(backend_root / "alembic.ini"))
        expected_head = ScriptDirectory.from_config(alembic_config).get_current_head()
        with get_engine().connect() as connection:
            version = connection.execute(text("SHOW server_version")).scalar_one()
            vector_version = connection.execute(
                text("SELECT extversion FROM pg_extension WHERE extname='vector'")
            ).scalar_one_or_none()
            if vector_version is None:
                print("FAIL: SQLAlchemy connected, but pgvector is not enabled.")
                return 1
            # These are three-dimensional test literals, not a BGE-M3 schema/dimension.
            distance = connection.execute(
                text("SELECT CAST('[1,0,0]' AS vector) <=> CAST('[1,0,0]' AS vector)")
            ).scalar_one()
            if distance != 0:
                print("FAIL: pgvector cosine distance smoke test failed.")
                return 1
            if not inspect(connection).has_table("alembic_version"):
                print("FAIL: pgvector works, but Alembic has not been applied.")
                return 1
            revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one_or_none()
            if revision != expected_head:
                print(
                    f"FAIL: database revision {revision!r} does not match "
                    f"Alembic head {expected_head!r}."
                )
                return 1
            required_tables = {"users", "appointments", "medical_records", "documents", "document_chunks"}
            if not required_tables.issubset(inspect(connection).get_table_names(schema="public")):
                print("FAIL: business schema is incomplete.")
                return 1
            vector_type = connection.execute(
                text(
                    "SELECT format_type(a.atttypid, a.atttypmod) "
                    "FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid "
                    "WHERE c.relname='document_chunks' AND a.attname='embedding' AND a.attnum > 0"
                )
            ).scalar_one_or_none()
            if vector_type != "vector(1024)":
                print("FAIL: document_chunks.embedding is not vector(1024).")
                return 1
        print(f"PASS: PostgreSQL {version}; SQLAlchemy connected; pgvector {vector_version}; cosine distance OK; Alembic {revision}.")
        return 0
    except SQLAlchemyError:
        print("FAIL: cannot verify database. Check local .env, PostgreSQL service, credentials and migrations; no secrets printed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
