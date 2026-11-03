"""Doctor persistence queries."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.care import Doctor
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

    def user_has_doctor_role(self, user_id: UUID) -> bool:
        return self.session.scalar(
            select(UserRole.user_id)
            .join(Role, Role.id == UserRole.role_id)
            .where(UserRole.user_id == user_id, Role.code == "DOCTOR", Role.is_active.is_(True))
        ) is not None

    def user_exists(self, user_id: UUID) -> bool:
        return self.session.get(User, user_id) is not None

    def add(self, doctor: Doctor) -> Doctor:
        self.session.add(doctor)
        return doctor
