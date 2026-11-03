"""User and persisted-role lookups shared by the actor dependency."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.identity import Role, User, UserRole


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, user_id: UUID) -> User | None:
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(func.lower(User.email) == email.lower()))

    def get_role(self, code: str) -> Role | None:
        return self.session.scalar(
            select(Role).where(Role.code == code, Role.is_active.is_(True))
        )

    def add(self, user: User) -> User:
        self.session.add(user)
        return user

    def assign_role(self, user: User, role: Role, assigned_by: UUID | None = None) -> UserRole:
        assignment = UserRole(user_id=user.id, role_id=role.id, assigned_by=assigned_by)
        self.session.add(assignment)
        return assignment

    def active_role_codes(self, user_id: UUID) -> frozenset[str]:
        return frozenset(
            self.session.scalars(
                select(Role.code)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == user_id, Role.is_active.is_(True))
            ).all()
        )
