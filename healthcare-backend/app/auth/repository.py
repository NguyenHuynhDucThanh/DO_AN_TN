"""Refresh-session persistence and rotation locking."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.identity import RefreshSession


class RefreshSessionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_hash(self, token_hash: str, *, for_update: bool = False) -> RefreshSession | None:
        statement = select(RefreshSession).where(RefreshSession.token_hash == token_hash)
        if for_update:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def add(self, refresh_session: RefreshSession) -> RefreshSession:
        self.session.add(refresh_session)
        return refresh_session

    def revoke_family(self, family_id: UUID, revoked_at: datetime) -> None:
        self.session.execute(
            update(RefreshSession)
            .where(
                RefreshSession.family_id == family_id,
                RefreshSession.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
