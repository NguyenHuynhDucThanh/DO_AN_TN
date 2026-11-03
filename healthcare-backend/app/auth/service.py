"""Registration, login, JWT issuance, refresh rotation, and logout."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.passwords import hash_password, needs_rehash, verify_password
from app.auth.repository import RefreshSessionRepository
from app.auth.schemas import LoginRequest, RegisterRequest, UserRead
from app.auth.tokens import (
    create_access_token,
    create_csrf_token,
    create_refresh_token,
    hash_refresh_token,
)
from app.core.config import get_settings
from app.core.errors import ConflictError, UnauthorizedError
from app.models.enums import UserStatus
from app.models.identity import RefreshSession, User
from app.users.repository import UserRepository


@dataclass(frozen=True, slots=True)
class AuthResult:
    user: UserRead
    access_token: str
    refresh_token: str
    csrf_token: str


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.refresh_sessions = RefreshSessionRepository(session)
        self.settings = get_settings()

    def _user_read(self, user: User) -> UserRead:
        return UserRead.model_validate(
            {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
                "date_of_birth": user.date_of_birth,
                "gender": user.gender,
                "status": user.status,
                "roles": sorted(self.users.active_role_codes(user.id)),
                "created_at": user.created_at,
                "updated_at": user.updated_at,
            }
        )

    def _new_session(
        self,
        user: User,
        *,
        user_agent: str | None,
        ip_address: str | None,
        family_id: UUID | None = None,
    ) -> tuple[RefreshSession, str]:
        raw_token = create_refresh_token()
        refresh_session = RefreshSession(
            user_id=user.id,
            family_id=family_id or uuid4(),
            token_hash=hash_refresh_token(raw_token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=self.settings.refresh_token_days),
            user_agent=user_agent[:500] if user_agent else None,
            ip_address=ip_address[:45] if ip_address else None,
        )
        self.refresh_sessions.add(refresh_session)
        return refresh_session, raw_token

    def _result(
        self,
        user: User,
        refresh_token: str,
    ) -> AuthResult:
        return AuthResult(
            user=self._user_read(user),
            access_token=create_access_token(user.id, settings=self.settings),
            refresh_token=refresh_token,
            csrf_token=create_csrf_token(),
        )

    def register(
        self,
        data: RegisterRequest,
        *,
        user_agent: str | None,
        ip_address: str | None,
    ) -> AuthResult:
        if self.users.get_by_email(str(data.email)) is not None:
            raise ConflictError("An account with this email already exists.", "email_exists")
        patient_role = self.users.get_role("PATIENT")
        if patient_role is None:
            raise ConflictError("The PATIENT role is not available.", "patient_role_unavailable")
        user = User(
            email=str(data.email).lower(),
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            phone=data.phone,
            date_of_birth=data.date_of_birth,
            gender=data.gender,
            status=UserStatus.ACTIVE,
        )
        self.users.add(user)
        try:
            self.session.flush()
            self.users.assign_role(user, patient_role)
            _, refresh_token = self._new_session(
                user, user_agent=user_agent, ip_address=ip_address
            )
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError(
                "An account with this email already exists.", "email_exists"
            ) from exc
        self.session.refresh(user)
        return self._result(user, refresh_token)

    def login(
        self,
        data: LoginRequest,
        *,
        user_agent: str | None,
        ip_address: str | None,
    ) -> AuthResult:
        user = self.users.get_by_email(str(data.email))
        if user is None or not verify_password(user.password_hash, data.password):
            raise UnauthorizedError("Email or password is incorrect.", "invalid_credentials")
        if user.status != UserStatus.ACTIVE:
            raise UnauthorizedError("This account is not active.", "inactive_user")
        if not self.users.active_role_codes(user.id):
            raise UnauthorizedError("This account has no active role.", "inactive_user")
        if needs_rehash(user.password_hash):
            user.password_hash = hash_password(data.password)
        _, refresh_token = self._new_session(
            user, user_agent=user_agent, ip_address=ip_address
        )
        self.session.commit()
        return self._result(user, refresh_token)

    def refresh(
        self,
        raw_token: str | None,
        *,
        user_agent: str | None,
        ip_address: str | None,
    ) -> AuthResult:
        if not raw_token:
            raise UnauthorizedError("A refresh session is required.", "refresh_required")
        now = datetime.now(timezone.utc)
        current = self.refresh_sessions.get_by_hash(
            hash_refresh_token(raw_token), for_update=True
        )
        if current is None:
            raise UnauthorizedError("The refresh session is invalid.", "invalid_refresh_token")
        if current.revoked_at is not None:
            if current.replaced_by_session_id is not None:
                self.refresh_sessions.revoke_family(current.family_id, now)
                self.session.commit()
                raise UnauthorizedError(
                    "Refresh-token reuse was detected; the session family was revoked.",
                    "refresh_token_reuse",
                )
            raise UnauthorizedError("The refresh session was revoked.", "revoked_session")
        if current.expires_at <= now:
            current.revoked_at = now
            self.session.commit()
            raise UnauthorizedError("The refresh session expired.", "expired_refresh_token")
        user = self.users.get(current.user_id)
        if user is None or user.status != UserStatus.ACTIVE:
            current.revoked_at = now
            self.session.commit()
            raise UnauthorizedError("This account is not active.", "inactive_user")
        if not self.users.active_role_codes(user.id):
            current.revoked_at = now
            self.session.commit()
            raise UnauthorizedError("This account has no active role.", "inactive_user")

        replacement, replacement_token = self._new_session(
            user,
            user_agent=user_agent,
            ip_address=ip_address,
            family_id=current.family_id,
        )
        self.session.flush()
        current.last_used_at = now
        current.revoked_at = now
        current.replaced_by_session_id = replacement.id
        self.session.commit()
        return self._result(user, replacement_token)

    def logout(self, raw_token: str | None) -> None:
        if not raw_token:
            return
        refresh_session = self.refresh_sessions.get_by_hash(
            hash_refresh_token(raw_token), for_update=True
        )
        if refresh_session is not None and refresh_session.revoked_at is None:
            refresh_session.revoked_at = datetime.now(timezone.utc)
            self.session.commit()
