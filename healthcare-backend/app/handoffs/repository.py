"""Handoff persistence."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.identity import Role, UserRole
from app.models.operations import HandoffRequest


class HandoffRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[HandoffRequest]:
        return list(self.session.scalars(select(HandoffRequest).order_by(HandoffRequest.created_at.desc())))

    def list_for_requester(self, requester_id: UUID) -> list[HandoffRequest]:
        return list(
            self.session.scalars(
                select(HandoffRequest)
                .where(HandoffRequest.requester_id == requester_id)
                .order_by(HandoffRequest.created_at.desc())
            )
        )

    def get(self, request_id: UUID, *, for_update: bool = False) -> HandoffRequest | None:
        statement = select(HandoffRequest).where(HandoffRequest.id == request_id)
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def can_handle(self, user_id: UUID) -> bool:
        return self.session.scalar(
            select(UserRole.user_id)
            .join(Role, Role.id == UserRole.role_id)
            .where(
                UserRole.user_id == user_id,
                Role.code.in_(["STAFF", "ADMIN"]),
                Role.is_active.is_(True),
            )
        ) is not None
