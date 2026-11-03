import pytest
from httpx import AsyncClient
from sqlalchemy.exc import OperationalError
from unittest.mock import MagicMock


pytestmark = pytest.mark.anyio


async def test_health_when_database_and_vector_are_ready(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok", "application": "healthcare-backend", "environment": "test"
    }


async def test_health_returns_503_without_leaking_connection_errors(client: AsyncClient, health_session: MagicMock) -> None:
    health_session.execute.side_effect = OperationalError(
        "SELECT 1", {}, Exception("postgresql://private_user:private_password@private_host/db")
    )
    response = await client.get("/api/v1/health")
    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"
    assert set(response.json()) == {"status", "application", "environment"}
    assert "private_" not in response.text


async def test_health_requires_pgvector(client: AsyncClient, health_session: MagicMock) -> None:
    health_session.execute.return_value.scalar_one_or_none.return_value = None
    assert (await client.get("/api/v1/health")).status_code == 503


async def test_cors_allows_only_configured_origin(client: AsyncClient) -> None:
    allowed = await client.options("/api/v1/health", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"
    })
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert allowed.headers["access-control-allow-credentials"] == "true"

    denied = await client.options("/api/v1/health", headers={
        "Origin": "http://untrusted.example", "Access-Control-Request-Method": "GET"
    })
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers


async def test_openapi_documents_health_and_failure(client: AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()
    operation = schema["paths"]["/api/v1/health"]["get"]
    assert "200" in operation["responses"]
    assert "503" in operation["responses"]
    serialized_schema = str(schema).lower()
    assert "password_hash" not in serialized_schema
    assert "jwt_secret" not in serialized_schema
    assert "database_url" not in serialized_schema
    assert "gemini_api_key" not in serialized_schema
