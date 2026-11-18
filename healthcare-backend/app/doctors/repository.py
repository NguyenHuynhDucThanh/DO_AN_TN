"""Doctor persistence queries."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.care import Doctor
from app.models.enums import UserStatus
from app.models.identity import Role, User, UserRole


class DoctorRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _load_statement():
        return select(Doctor).options(selectinload(Doctor.user), selectinload(Doctor.specialty))

    def list(self, specialty_id: UUID | None = None, active_only: bool | None = None) -> list[Doctor]:
        statement = self._load_statement().order_by(Doctor.created_at)
        if specialty_id is not None:
            statement = statement.where(Doctor.specialty_id == specialty_id)
        if active_only is not None:
            statement = statement.where(Doctor.is_active.is_(active_only))
        return list(self.session.scalars(statement))

    def get(self, doctor_id: UUID) -> Doctor | None:
        return self.session.scalar(self._load_statement().where(Doctor.id == doctor_id))

    def get_by_user_id(self, user_id: UUID) -> Doctor | None:
        return self.session.scalar(self._load_statement().where(Doctor.user_id == user_id))

    def get_user(self, user_id: UUID) -> User | None:
        return self.session.get(User, user_id)

    def list_candidates(self) -> list[User]:
        statement = (
            select(User)
            .join(UserRole, UserRole.user_id == User.id)
            .join(Role, Role.id == UserRole.role_id)
            .outerjoin(Doctor, Doctor.user_id == User.id)
            .where(
                User.status == UserStatus.ACTIVE,
                Role.code == "DOCTOR",
                Role.is_active.is_(True),
                Doctor.id.is_(None),
            )
            .order_by(User.full_name, User.email)
        )
        return list(self.session.scalars(statement))

    def user_has_doctor_role(self, user_id: UUID) -> bool:
        return self.session.scalar(
            select(UserRole.user_id)
            .join(Role, Role.id == UserRole.role_id)
            .where(UserRole.user_id == user_id, Role.code == "DOCTOR", Role.is_active.is_(True))
        ) is not None

    def add(self, doctor: Doctor) -> Doctor:
        self.session.add(doctor)
        return doctor
