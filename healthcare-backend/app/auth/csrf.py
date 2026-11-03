"""CSRF double-submit and exact-Origin checks for cookie-authenticated writes."""

import secrets

from fastapi import Request

from app.core.config import Settings, get_settings
from app.core.errors import ForbiddenError

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


def validate_origin(
    request: Request, *, settings: Settings | None = None, required: bool = True
) -> None:
    config = settings or get_settings()
    origin = request.headers.get("origin")
    if origin is None and not required:
        return
    if origin != config.frontend_origin:
        raise ForbiddenError("The request origin is not allowed.", "invalid_origin")


def validate_csrf(request: Request, *, settings: Settings | None = None) -> None:
    if request.method.upper() in SAFE_METHODS:
        return
    config = settings or get_settings()
    validate_origin(request, settings=config)
    cookie_token = request.cookies.get(config.csrf_cookie_name)
    header_token = request.headers.get("X-CSRF-Token")
    if (
        not cookie_token
        or not header_token
        or not secrets.compare_digest(cookie_token, header_token)
    ):
        raise ForbiddenError("CSRF validation failed.", "csrf_failed")
