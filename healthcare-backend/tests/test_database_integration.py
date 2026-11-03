import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Engine, inspect, text

pytestmark = pytest.mark.integration


def test_postgresql_pgvector_and_migration(real_database: Engine) -> None:
    with real_database.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
        assert connection.execute(text("SELECT extname FROM pg_extension WHERE extname='vector'")).scalar_one() == "vector"
        # Literal smoke test is independent of the BGE-M3 column dimension.
        assert connection.execute(text("SELECT CAST('[1,0,0]' AS vector) <=> CAST('[1,0,0]' AS vector)")).scalar_one() == pytest.approx(0)
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0004_add_json_document_type"
        expected_tables = {
            "alembic_version", "appointments", "audit_logs", "doctor_schedules", "doctors",
            "document_chunks", "documents", "handoff_requests", "medical_records", "refresh_sessions",
            "roles", "schedule_slots", "specialties", "user_roles", "users",
        }
        assert set(inspect(connection).get_table_names(schema="public")) == expected_tables


@pytest.mark.anyio
async def test_health_against_real_database(real_database: Engine) -> None:
    from app.main import create_app
    async with AsyncClient(transport=ASGITransport(app=create_app()), base_url="http://testserver") as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
