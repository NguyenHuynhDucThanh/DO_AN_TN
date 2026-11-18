"""Resolve a verified cookie/JWT identity into the existing ActorContext."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request, WebSocket
from sqlalchemy.orm import Session

from app.auth.context import ActorContext
from app.auth.csrf import validate_csrf
from app.auth.tokens import decode_access_token
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import UnauthorizedError
from app.models.enums import UserStatus
from app.users.repository import UserRepository


def get_current_actor(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    dev_user_id: Annotated[UUID | None, Header(alias="X-Dev-User-Id")] = None,
) -> ActorContext:
    """Use JWT first; a malformed JWT never falls back to development identity."""
    settings = get_settings()
    access_token = request.cookies.get(settings.access_cookie_name)
    if access_token is not None:
        user_id = decode_access_token(access_token, settings=settings)
        validate_csrf(request, settings=settings)
    elif settings.app_env != "production" and settings.dev_auth_enabled and dev_user_id is not None:
        user_id = dev_user_id
    else:
        raise UnauthorizedError()

    users = UserRepository(db)
    user = users.get(user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise UnauthorizedError("The authenticated user is missing or inactive.", "inactive_user")
    roles = users.active_role_codes(user_id)
    if not roles:
        raise UnauthorizedError("The authenticated user has no active role.", "inactive_user")
    return ActorContext(user_id=user.id, roles=roles)


def get_websocket_actor(websocket: WebSocket, db: Session) -> ActorContext:
    """Authenticate WebSocket by cookie, or an explicit development-only identity."""
    settings = get_settings()
    if websocket.headers.get("origin") != settings.frontend_origin:
        raise UnauthorizedError("The WebSocket origin is not allowed.", "invalid_origin")
    access_token = websocket.cookies.get(settings.access_cookie_name)
    if access_token is not None:
        user_id = decode_access_token(access_token, settings=settings)
    elif settings.app_env != "production" and settings.dev_auth_enabled:
        raw_dev_user_id = websocket.query_params.get("dev_user_id")
        try:
            user_id = UUID(raw_dev_user_id) if raw_dev_user_id else None
        except ValueError:
            user_id = None
        if user_id is None:
            raise UnauthorizedError()
    else:
        raise UnauthorizedError()
    users = UserRepository(db)
    user = users.get(user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise UnauthorizedError("The authenticated user is missing or inactive.", "inactive_user")
    roles = users.active_role_codes(user_id)
    if not roles:
        raise UnauthorizedError("The authenticated user has no active role.", "inactive_user")
    return ActorContext(user_id=user.id, roles=roles)
