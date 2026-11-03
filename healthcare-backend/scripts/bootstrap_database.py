"""Create an isolated development role/database; never reset existing credentials."""

import argparse
import getpass
from pathlib import Path
import secrets
import sys

import psycopg
from psycopg import sql
from dotenv import dotenv_values, set_key
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = BACKEND_ROOT / ".env"


def bootstrap(host: str, port: int, admin_user: str) -> None:
    env = dotenv_values(ENV_PATH)
    raw_url = env.get("DATABASE_URL")
    if not raw_url:
        raise RuntimeError("Create .env from .env.example before bootstrap.")
    try:
        app_url = make_url(raw_url)
    except ArgumentError:
        raise RuntimeError("DATABASE_URL is invalid; review local .env.") from None
    if app_url.drivername != "postgresql+psycopg":
        raise RuntimeError("DATABASE_URL must use postgresql+psycopg.")
    if app_url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("This development bootstrap only supports a local PostgreSQL server.")
    if app_url.port not in {None, port} or app_url.host != host:
        raise RuntimeError("Bootstrap host/port must match DATABASE_URL.")
    if not app_url.username or not app_url.database or app_url.username == admin_user:
        raise RuntimeError("Configure a dedicated application username and database in .env.")

    admin_password = getpass.getpass("PostgreSQL administrator password (hidden): ")
    with psycopg.connect(
        host=host, port=port, user=admin_user, password=admin_password,
        dbname="postgres", connect_timeout=5, autocommit=True,
    ) as conn:
        if conn.execute("SELECT 1 FROM pg_available_extensions WHERE name='vector'").fetchone() is None:
            raise RuntimeError(
                "pgvector server extension is missing. Install it with scripts/install_pgvector.ps1 "
                "in an Administrator PowerShell, then retry. No role/database was created."
            )
        role_exists = conn.execute(
            "SELECT 1 FROM pg_roles WHERE rolname=%s", (app_url.username,)
        ).fetchone() is not None
        db_owner = conn.execute(
            "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s",
            (app_url.database,),
        ).fetchone()
        app_password = app_url.password
        if role_exists and (not app_password or app_password == "CHANGE_ME"):
            raise RuntimeError("Application role already exists. Put its current password in .env; it will not be reset.")
        if db_owner and db_owner[0] != app_url.username:
            raise RuntimeError("Database already exists with a different owner; nothing will be overwritten.")
        if not role_exists:
            app_password = secrets.token_urlsafe(32)
            conn.execute(
                sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE").format(
                    sql.Identifier(app_url.username), sql.Literal(app_password)
                )
            )
            # Persist generated app credentials immediately so a retry after a DB error is possible.
            new_url = URL.create(
                "postgresql+psycopg", username=app_url.username, password=app_password,
                host=host, port=port, database=app_url.database,
            )
            set_key(str(ENV_PATH), "DATABASE_URL", new_url.render_as_string(hide_password=False))
        if not db_owner:
            conn.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(
                sql.Identifier(app_url.database), sql.Identifier(app_url.username)
            ))

    with psycopg.connect(
        host=host, port=port, user=admin_user, password=admin_password,
        dbname=app_url.database, connect_timeout=5, autocommit=True,
    ) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        extension = conn.execute("SELECT extversion FROM pg_extension WHERE extname='vector'").fetchone()
    print(f"Development database ready; pgvector {extension[0]} enabled.")
    print("Application connection saved to local .env; administrator password was not saved.")
    print("Next: .venv\\Scripts\\python.exe -m alembic upgrade head")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--admin-user", default="postgres")
    args = parser.parse_args()
    try:
        bootstrap(args.host, args.port, args.admin_user)
    except psycopg.Error as exc:
        # Do not print DSNs, authentication details or SQL containing passwords.
        print(f"PostgreSQL operation failed (SQLSTATE {exc.sqlstate or 'connection error'}). Check server, credentials and privileges.", file=sys.stderr)
        return 1
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("Bootstrap cancelled; no administrator password was saved.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
