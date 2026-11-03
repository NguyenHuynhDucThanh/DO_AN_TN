"""Short-lived booking confirmations bound to one authenticated actor and slot."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import jwt

from app.core.config import Settings
from app.core.errors import BadRequestError, ForbiddenError

ALGORITHM = "HS256"


def create_booking_confirmation(
    actor_id: UUID, slot_id: UUID, settings: Settings, *, now: datetime | None = None
) -> str:
    issued_at = now or datetime.now(timezone.utc)
    payload = {
        "sub": str(actor_id),
        "slot_id": str(slot_id),
        "type": "booking_confirmation",
        "jti": str(uuid4()),
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=settings.tool_confirmation_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=ALGORITHM)


def decode_booking_confirmation(token: str, actor_id: UUID, settings: Settings) -> UUID:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[ALGORITHM],
            options={"require": ["sub", "slot_id", "type", "jti", "iat", "exp"]},
        )
        if payload.get("type") != "booking_confirmation":
            raise BadRequestError("Booking confirmation is invalid.", "invalid_confirmation")
        if UUID(payload["sub"]) != actor_id:
            raise ForbiddenError(
                "This booking confirmation belongs to another user.",
                "confirmation_actor_mismatch",
            )
        return UUID(payload["slot_id"])
    except (BadRequestError, ForbiddenError):
        raise
    except (jwt.PyJWTError, ValueError, TypeError, KeyError) as exc:
        raise BadRequestError(
            "Booking confirmation is invalid or expired.", "invalid_confirmation"
        ) from exc

