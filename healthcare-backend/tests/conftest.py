"""Unit tests use isolated settings; integration tests explicitly opt into local DB."""

import os
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import Session


@pytest.fixture
def health_session() -> MagicMock:
    session = MagicMock(spec=Session)
    session.execute.return_value.scalar_one_or_none.return_value = "vector"
    return session


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch, health_session: MagicMock):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unit:unit@localhost:5432/unit_test")
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://localhost:5173")
    from app.core.config import get_settings
    get_settings.cache_clear()
    from app.core.database import get_db
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_db] = lambda: health_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as test_client:
        yield test_client
    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture
def real_database():
    if os.getenv("RUN_DB_INTEGRATION") != "1":
        pytest.skip("Set RUN_DB_INTEGRATION=1 to test the real development database")
    from app.core.config import get_settings
    from app.core.database import get_engine, get_session_factory

    get_settings.cache_clear()
    get_session_factory.cache_clear()
    get_engine.cache_clear()
    engine = get_engine()
    yield engine
    engine.dispose()
    get_session_factory.cache_clear()
    get_engine.cache_clear()
    get_settings.cache_clear()
