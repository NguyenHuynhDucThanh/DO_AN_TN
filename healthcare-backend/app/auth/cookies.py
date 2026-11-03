"""Centralized HttpOnly authentication-cookie policy."""

from fastapi import Response

from app.core.config import Settings, get_settings


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    csrf_token: str,
    *,
    settings: Settings | None = None,
) -> None:
    config = settings or get_settings()
    common = {
        "secure": config.cookie_secure,
        "samesite": "lax",
    }
    response.set_cookie(
        config.access_cookie_name,
        access_token,
        max_age=config.access_token_minutes * 60,
        httponly=True,
        path="/api/v1",
        **common,
    )
    response.set_cookie(
        config.refresh_cookie_name,
        refresh_token,
        max_age=config.refresh_token_days * 24 * 60 * 60,
        httponly=True,
        path="/api/v1/auth",
        **common,
    )
    response.set_cookie(
        config.csrf_cookie_name,
        csrf_token,
        max_age=config.refresh_token_days * 24 * 60 * 60,
        httponly=False,
        path="/",
        **common,
    )


def clear_auth_cookies(response: Response, *, settings: Settings | None = None) -> None:
    config = settings or get_settings()
    response.delete_cookie(config.access_cookie_name, path="/api/v1")
    response.delete_cookie(config.refresh_cookie_name, path="/api/v1/auth")
    response.delete_cookie(config.csrf_cookie_name, path="/")
