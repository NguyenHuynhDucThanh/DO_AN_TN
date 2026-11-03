"""Cookie-based authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.auth.context import ActorContext
from app.auth.cookies import clear_auth_cookies, set_auth_cookies
from app.auth.csrf import validate_csrf, validate_origin
from app.auth.dependencies import get_current_actor
from app.auth.schemas import LoginRequest, RegisterRequest, SessionResponse, UserRead
from app.auth.service import AuthResult, AuthService
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import UnauthorizedError
from app.core.rate_limit import enforce_rate_limit
from app.models.enums import UserStatus
from app.users.repository import UserRepository

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _client_metadata(request: Request) -> tuple[str | None, str | None]:
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None
    return user_agent, ip_address


def _apply_auth_result(response: Response, result: AuthResult) -> SessionResponse:
    set_auth_cookies(
        response,
        result.access_token,
        result.refresh_token,
        result.csrf_token,
    )
    response.headers["Cache-Control"] = "no-store"
    return SessionResponse(user=result.user)


@router.post("/register", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def register(
    data: RegisterRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> SessionResponse:
    validate_origin(request, required=False)
    settings = get_settings()
    enforce_rate_limit(
        request,
        scope="auth_register",
        identity=str(data.email),
        limit=settings.register_rate_limit,
        window_seconds=settings.common_rate_window_seconds,
        enabled=settings.rate_limit_enabled,
    )
    user_agent, ip_address = _client_metadata(request)
    result = AuthService(db).register(
        data, user_agent=user_agent, ip_address=ip_address
    )
    return _apply_auth_result(response, result)


@router.post("/login", response_model=SessionResponse)
def login(
    data: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> SessionResponse:
    validate_origin(request, required=False)
    settings = get_settings()
    enforce_rate_limit(
        request,
        scope="auth_login",
        identity=str(data.email),
        limit=settings.login_rate_limit,
        window_seconds=settings.login_rate_window_seconds,
        enabled=settings.rate_limit_enabled,
    )
    user_agent, ip_address = _client_metadata(request)
    result = AuthService(db).login(data, user_agent=user_agent, ip_address=ip_address)
    return _apply_auth_result(response, result)


@router.post("/refresh", response_model=SessionResponse)
def refresh(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> SessionResponse:
    validate_csrf(request)
    settings = get_settings()
    enforce_rate_limit(
        request,
        scope="auth_refresh",
        limit=settings.refresh_rate_limit,
        window_seconds=settings.common_rate_window_seconds,
        enabled=settings.rate_limit_enabled,
    )
    user_agent, ip_address = _client_metadata(request)
    result = AuthService(db).refresh(
        request.cookies.get(settings.refresh_cookie_name),
        user_agent=user_agent,
        ip_address=ip_address,
    )
    return _apply_auth_result(response, result)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    validate_csrf(request)
    settings = get_settings()
    AuthService(db).logout(request.cookies.get(settings.refresh_cookie_name))
    clear_auth_cookies(response, settings=settings)
    response.headers["Cache-Control"] = "no-store"


@router.get("/me", response_model=UserRead)
def me(
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
) -> UserRead:
    user = UserRepository(db).get(actor.user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise UnauthorizedError()
    return UserRead.model_validate(
        {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "date_of_birth": user.date_of_birth,
            "gender": user.gender,
            "status": user.status,
            "roles": sorted(actor.roles),
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
    )
