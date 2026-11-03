"""Phase 3 endpoints remain closed without the controlled actor dependency."""

import pytest


@pytest.mark.anyio
async def test_protected_endpoint_requires_actor(client) -> None:
    response = await client.get("/api/v1/appointments")
    assert response.status_code == 401
    assert response.json() == {
        "error": {"code": "unauthorized", "detail": "Authentication is required."}
    }


@pytest.mark.anyio
async def test_medical_record_is_not_public(client) -> None:
    response = await client.get("/api/v1/medical-records/me/history")
    assert response.status_code == 401
