import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize("origin", ["*", "https://*.example.com", "https://example.com/path", "https://user:password@example.com", "https://example.com?query=1"])
def test_rejects_non_exact_cors_origin(origin: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="postgresql+psycopg://user:password@localhost/dev", frontend_origin=origin)


def test_settings_repr_and_errors_do_not_expose_database_secret() -> None:
    settings = Settings(_env_file=None, database_url="postgresql+psycopg://user:secret_value@localhost/dev")
    assert "secret_value" not in repr(settings)
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, database_url="invalid_secret_value")
    assert "invalid_secret_value" not in str(error.value)


def test_rejects_other_database_backends() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="sqlite:///dev.db")


def test_gemini_configuration_is_optional_and_secret_is_hidden() -> None:
    business_only = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://user:password@localhost/dev",
    )
    assert business_only.gemini_api_key is None
    assert business_only.gemini_model is None

    configured = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://user:password@localhost/dev",
        gemini_api_key="private-gemini-key",
        gemini_model="configured-model",
    )
    assert "private-gemini-key" not in repr(configured)


@pytest.mark.parametrize(
    ("field", "value"),
    [("gemini_model", "invalid model"), ("gemini_timeout_seconds", 0)],
)
def test_rejects_invalid_gemini_configuration(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url="postgresql+psycopg://user:password@localhost/dev",
            **{field: value},
        )
