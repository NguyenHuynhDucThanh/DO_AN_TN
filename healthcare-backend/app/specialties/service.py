"""Specialty business rules."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.context import ActorContext
from app.core.errors import ConflictError, NotFoundError
from app.models.care import Specialty
from app.specialties.repository import SpecialtyRepository
from app.specialties.schemas import SpecialtyCreate, SpecialtyStatusUpdate, SpecialtyUpdate


class SpecialtyService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = SpecialtyRepository(session)

    def list(self, active_only: bool | None = None) -> list[Specialty]:
        return self.repository.list(active_only)

    def search(self, query: str) -> list[Specialty]:
        """Search active specialties without exposing persistence details to AI adapters."""
        normalized = query.strip().casefold()
        if not normalized:
            raise ValueError("Specialty query must not be empty")
        return [
            specialty
            for specialty in self.list(active_only=True)
            if normalized
            in " ".join(
                filter(None, (specialty.code, specialty.name, specialty.description))
            ).casefold()
        ]

    def get(self, specialty_id: UUID) -> Specialty:
        specialty = self.repository.get(specialty_id)
        if specialty is None:
            raise NotFoundError("Specialty was not found.", "specialty_not_found")
        return specialty

    def create(self, data: SpecialtyCreate, actor: ActorContext) -> Specialty:
        actor.require_any_role("ADMIN")
        if self.repository.get_by_code_or_name(data.code, data.name):
            raise ConflictError("Specialty code or name already exists.", "specialty_exists")
        specialty = Specialty(**data.model_dump())
        self.repository.add(specialty)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("Specialty code or name already exists.", "specialty_exists") from exc
        self.session.refresh(specialty)
        return specialty

    def update(self, specialty_id: UUID, data: SpecialtyUpdate, actor: ActorContext) -> Specialty:
        actor.require_any_role("ADMIN")
        specialty = self.get(specialty_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(specialty, field, value.strip() if isinstance(value, str) else value)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("Specialty name already exists.", "specialty_exists") from exc
        self.session.refresh(specialty)
        return specialty

    def set_status(
        self, specialty_id: UUID, data: SpecialtyStatusUpdate, actor: ActorContext
    ) -> Specialty:
        actor.require_any_role("ADMIN")
        specialty = self.get(specialty_id)
        specialty.is_active = data.is_active
        self.session.commit()
        self.session.refresh(specialty)
        return specialty
