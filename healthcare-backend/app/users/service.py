"""Authenticated profile operations without role or email mutation."""

from sqlalchemy.orm import Session

from app.auth.context import ActorContext
from app.auth.schemas import UserRead
from app.core.errors import BadRequestError, NotFoundError
from app.models.identity import User
from app.users.repository import UserRepository
from app.users.schemas import UserProfileUpdate


class UserService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = UserRepository(session)

    def _read(self, user: User, roles: frozenset[str]) -> UserRead:
        return UserRead.model_validate(
            {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "phone": user.phone,
                "date_of_birth": user.date_of_birth,
                "gender": user.gender,
                "status": user.status,
                "roles": sorted(roles),
                "created_at": user.created_at,
                "updated_at": user.updated_at,
            }
        )

    def update_me(self, data: UserProfileUpdate, actor: ActorContext) -> UserRead:
        user = self.repository.get(actor.user_id)
        if user is None:
            raise NotFoundError("User was not found.", "user_not_found")
        changes = data.model_dump(exclude_unset=True)
        if "phone" in changes and changes["phone"] is None and actor.has_any_role("PATIENT"):
            raise BadRequestError("Patient phone cannot be removed.", "patient_phone_required")
        for field, value in changes.items():
            setattr(user, field, value)
        self.session.commit()
        self.session.refresh(user)
        return self._read(user, actor.roles)
