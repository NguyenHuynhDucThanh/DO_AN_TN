"""Short-lived JWT access tokens and opaque refresh-token helpers."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import secrets
from uuid import UUID, uuid4

import jwt

from app.core.config import Settings, get_settings
from app.core.errors import UnauthorizedError

JWT_ALGORITHM = "HS256"


def create_access_token(
    user_id: UUID, *, settings: Settings | None = None, now: datetime | None = None
) -> str:
    config = settings or get_settings()
    issued_at = now or datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "jti": str(uuid4()),
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=config.access_token_minutes),
    }
    return jwt.encode(payload, config.jwt_secret.get_secret_value(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str, *, settings: Settings | None = None) -> UUID:
    config = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            config.jwt_secret.get_secret_value(),
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "type", "jti", "iat", "exp"]},
        )
        if payload.get("type") != "access":
            raise UnauthorizedError("The access token is invalid.", "invalid_access_token")
        return UUID(payload["sub"])
    except UnauthorizedError:
        raise
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise UnauthorizedError(
            "The access token is invalid or expired.", "invalid_access_token"
        ) from exc


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def create_csrf_token() -> str:
    return secrets.token_urlsafe(32)
