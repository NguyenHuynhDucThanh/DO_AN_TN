"""Framework-independent identity passed into Phase 3 services."""

from dataclasses import dataclass
from uuid import UUID

from app.core.errors import ForbiddenError


@dataclass(frozen=True, slots=True)
class ActorContext:
    user_id: UUID
    roles: frozenset[str]

    def has_any_role(self, *roles: str) -> bool:
        return bool(self.roles.intersection(roles))

    def require_any_role(self, *roles: str) -> None:
        if not self.has_any_role(*roles):
            raise ForbiddenError()
