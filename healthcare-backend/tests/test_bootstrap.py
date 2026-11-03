from unittest.mock import MagicMock

import pytest

from scripts import bootstrap_database


def test_bootstrap_does_not_create_anything_if_pgvector_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bootstrap_database, "dotenv_values", lambda path: {
        "DATABASE_URL": "postgresql+psycopg://healthcare_app:CHANGE_ME@localhost:5432/healthcare_dev"
    })
    monkeypatch.setattr(bootstrap_database.getpass, "getpass", lambda prompt: "not-a-real-password")
    connection = MagicMock()
    connection.execute.return_value.fetchone.return_value = None
    context = MagicMock()
    context.__enter__.return_value = connection
    monkeypatch.setattr(bootstrap_database.psycopg, "connect", lambda **kwargs: context)

    with pytest.raises(RuntimeError, match="pgvector server extension is missing"):
        bootstrap_database.bootstrap("localhost", 5432, "postgres")
    assert connection.execute.call_count == 1
    assert "pg_available_extensions" in connection.execute.call_args.args[0]


def test_bootstrap_does_not_reset_existing_role_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bootstrap_database, "dotenv_values", lambda path: {
        "DATABASE_URL": "postgresql+psycopg://healthcare_app:CHANGE_ME@localhost:5432/healthcare_dev"
    })
    monkeypatch.setattr(bootstrap_database.getpass, "getpass", lambda prompt: "not-a-real-password")
    connection = MagicMock()
    connection.execute.return_value.fetchone.side_effect = [(1,), (1,), ("healthcare_app",)]
    context = MagicMock()
    context.__enter__.return_value = connection
    monkeypatch.setattr(bootstrap_database.psycopg, "connect", lambda **kwargs: context)

    with pytest.raises(RuntimeError, match="already exists"):
        bootstrap_database.bootstrap("localhost", 5432, "postgres")
    assert all("CREATE" not in call.args[0] and "ALTER" not in call.args[0] for call in connection.execute.call_args_list)
