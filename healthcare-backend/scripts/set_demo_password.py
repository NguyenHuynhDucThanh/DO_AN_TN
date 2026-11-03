"""Set an Argon2 password for one synthetic demo account without echoing it."""

from __future__ import annotations

import argparse
from getpass import getpass
from pathlib import Path
import sys

from sqlalchemy import func, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth.passwords import hash_password
from app.auth.schemas import _validate_password_strength
from app.core.config import get_settings
from app.core.database import get_session_factory
from app.models.identity import User


def main() -> None:
    parser = argparse.ArgumentParser(description="Set a password for a synthetic @example.invalid account.")
    parser.add_argument("email", help="Synthetic demo account email")
    args = parser.parse_args()
    email = args.email.strip().lower()
    if get_settings().app_env == "production":
        raise SystemExit("This development utility is disabled in production.")
    if not email.endswith("@example.invalid"):
        raise SystemExit("Only synthetic @example.invalid accounts are accepted.")
    password = getpass("New demo password: ")
    confirmation = getpass("Confirm demo password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    if not 8 <= len(password) <= 128:
        raise SystemExit("Password must contain between 8 and 128 characters.")
    try:
        _validate_password_strength(password)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    with get_session_factory()() as session, session.begin():
        user = session.scalar(select(User).where(func.lower(User.email) == email))
        if user is None:
            raise SystemExit("Synthetic demo account was not found. Run seed_demo.py first.")
        user.password_hash = hash_password(password)
    print(f"PASS: Argon2 password configured for {email}.")


if __name__ == "__main__":
    main()
