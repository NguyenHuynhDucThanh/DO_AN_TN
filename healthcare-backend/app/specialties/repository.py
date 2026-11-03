"""Specialty persistence queries."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.care import Specialty


class SpecialtyRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, active_only: bool | None = None) -> list[Specialty]:
        statement = select(Specialty).order_by(Specialty.name)
        if active_only is not None:
            statement = statement.where(Specialty.is_active.is_(active_only))
        return list(self.session.scalars(statement))

    def get(self, specialty_id: UUID) -> Specialty | None:
        return self.session.get(Specialty, specialty_id)

    def get_by_code_or_name(self, code: str, name: str) -> Specialty | None:
        return self.session.scalar(
            select(Specialty).where(
                (Specialty.code == code) | (func.lower(Specialty.name) == name.lower())
            )
        )

    def add(self, specialty: Specialty) -> Specialty:
        self.session.add(specialty)
        return specialty
