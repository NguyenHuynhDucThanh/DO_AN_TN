"""Phase 13 security boundaries that do not require external providers."""

from pathlib import Path

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.core.errors import TooManyRequestsError
from app.core.config import Settings
from app.core.rate_limit import RateLimiter, enforce_rate_limit, rate_limiter
from app.documents.loaders import load_csv
from app.main import create_app


def test_rate_limiter_is_scoped_hashed_and_recovers_after_window() -> None:
    current = [100.0]
    limiter = RateLimiter(clock=lambda: current[0], max_keys=10)
    for _ in range(2):
        limiter.check(
            scope="login",
            client="127.0.0.1",
            identity="patient@example.invalid",
            limit=2,
            window_seconds=60,
        )
    with pytest.raises(TooManyRequestsError) as raised:
        limiter.check(
            scope="login",
            client="127.0.0.1",
            identity="patient@example.invalid",
            limit=2,
            window_seconds=60,
        )
    assert raised.value.status_code == 429
    assert raised.value.code == "rate_limit_exceeded"
    assert raised.value.retry_after_seconds == 60

    current[0] = 161.0
    limiter.check(
        scope="login",
        client="127.0.0.1",
        identity="patient@example.invalid",
        limit=2,
        window_seconds=60,
    )


def test_unexpected_error_is_sanitized_and_security_headers_are_present() -> None:
    application = create_app()

    @application.get("/phase13-ok")
    def ok() -> dict[str, bool]:
        return {"ok": True}

    @application.get("/phase13-boom")
    def boom() -> None:
        raise RuntimeError("sensitive-provider-detail")

    with TestClient(application, raise_server_exceptions=False) as client:
        normal = client.get("/phase13-ok")
        failed = client.get("/phase13-boom")

    assert normal.headers["x-content-type-options"] == "nosniff"
    assert normal.headers["x-frame-options"] == "DENY"
    assert normal.headers["referrer-policy"] == "no-referrer"
    assert failed.status_code == 500
    assert failed.json() == {
        "error": {
            "code": "internal_server_error",
            "detail": "An unexpected server error occurred.",
        }
    }
    assert "sensitive-provider-detail" not in failed.text


def test_rate_limit_http_contract_is_safe_and_has_retry_after() -> None:
    rate_limiter.clear()
    application = create_app()

    @application.get("/phase13-limit")
    def limited(request: Request) -> dict[str, bool]:
        enforce_rate_limit(
            request,
            scope="phase13_test",
            limit=1,
            window_seconds=60,
        )
        return {"ok": True}

    with TestClient(application, raise_server_exceptions=False) as client:
        assert client.get("/phase13-limit").status_code == 200
        rejected = client.get("/phase13-limit")
    assert rejected.status_code == 429
    assert rejected.headers["retry-after"] == "60"
    assert rejected.json()["error"]["code"] == "rate_limit_exceeded"
    rate_limiter.clear()


def test_csv_negative_sample_never_enters_content_or_metadata(tmp_path: Path) -> None:
    source = tmp_path / "dataset.csv"
    source.write_text(
        "positive,negative,anchor,article_id,category,title\n"
        '"Nội dung y khoa đã xác nhận","Nội dung đối chứng không dùng","hỏi tự nhiên",42,"demo","Tiêu đề"\n',
        encoding="utf-8",
    )
    loaded = list(load_csv(source))
    assert len(loaded) == 1
    assert loaded[0].content == "Nội dung y khoa đã xác nhận"
    assert "negative" not in loaded[0].metadata
    assert "Nội dung đối chứng không dùng" not in str(loaded[0])
    assert loaded[0].metadata["anchor"] == "hỏi tự nhiên"


def test_sensitive_ai_tool_names_do_not_exist() -> None:
    ai_root = Path(__file__).resolve().parents[1] / "app" / "ai"
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in ai_root.rglob("*.py")
    ).casefold()
    for forbidden in (
        "get_medical_record",
        "search_patient_history",
        "summarize_medical_record",
        "update_medical_record",
    ):
        assert forbidden not in source


def test_production_cannot_disable_rate_limiting() -> None:
    with pytest.raises(ValueError, match="RATE_LIMIT_ENABLED"):
        Settings(
            app_env="production",
            database_url="postgresql+psycopg://app:password@localhost/healthcare",
            frontend_origin="https://healthcare.example",
            jwt_secret="production-secret-that-is-longer-than-thirty-two-characters",
            dev_auth_enabled=False,
            cookie_secure=True,
            rate_limit_enabled=False,
        )
