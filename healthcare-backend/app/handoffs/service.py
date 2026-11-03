"""Handoff ticket authorization and state transitions."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.context import ActorContext
from app.core.errors import ConflictError, ForbiddenError, NotFoundError
from app.handoffs.repository import HandoffRepository
from app.handoffs.schemas import HandoffCreate, HandoffUpdate
from app.models.enums import HandoffPriority, HandoffStatus
from app.models.operations import AuditLog, HandoffRequest


class HandoffService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = HandoffRepository(session)

    def create(self, data: HandoffCreate, actor: ActorContext) -> HandoffRequest:
        priority = data.priority if actor.has_any_role("STAFF", "ADMIN") else HandoffPriority.NORMAL
        return self._create(
            requester_id=actor.user_id,
            reason=data.reason.strip(),
            source=data.source.strip().upper(),
            priority=priority,
        )

    def create_risk_alert(
        self, rule_codes: tuple[str, ...], actor: ActorContext
    ) -> HandoffRequest:
        """Create an urgent system-classified ticket without storing the user's message."""
        safe_codes = ", ".join(rule_codes)
        return self._create(
            requester_id=actor.user_id,
            reason=f"Risk Alert demo triggered ({safe_codes}); staff review requested.",
            source="RISK_ALERT",
            priority=HandoffPriority.URGENT,
        )

    def _create(
        self,
        *,
        requester_id: UUID,
        reason: str,
        source: str,
        priority: HandoffPriority,
    ) -> HandoffRequest:
        request = HandoffRequest(
            requester_id=requester_id,
            reason=reason,
            source=source,
            priority=priority,
            status=HandoffStatus.PENDING,
        )
        self.session.add(request)
        self.session.commit()
        self.session.refresh(request)
        return request

    def list(self, actor: ActorContext) -> list[HandoffRequest]:
        if actor.has_any_role("STAFF", "ADMIN"):
            return self.repository.list_all()
        return self.repository.list_for_requester(actor.user_id)

    def get(self, request_id: UUID, actor: ActorContext) -> HandoffRequest:
        request = self.repository.get(request_id)
        if request is None:
            raise NotFoundError("Handoff request was not found.", "handoff_not_found")
        if request.requester_id != actor.user_id and not actor.has_any_role("STAFF", "ADMIN"):
            raise ForbiddenError()
        return request

    def update(
        self, request_id: UUID, data: HandoffUpdate, actor: ActorContext
    ) -> HandoffRequest:
        actor.require_any_role("STAFF", "ADMIN")
        request = self.repository.get(request_id, for_update=True)
        if request is None:
            raise NotFoundError("Handoff request was not found.", "handoff_not_found")
        transitions = {
            HandoffStatus.PENDING: {HandoffStatus.IN_PROGRESS},
            HandoffStatus.IN_PROGRESS: {HandoffStatus.RESOLVED},
            HandoffStatus.RESOLVED: set(),
        }
        if data.status != request.status and data.status not in transitions[request.status]:
            raise ConflictError("Invalid handoff state transition.", "invalid_handoff_transition")
        assignee = data.assigned_to if data.assigned_to is not None else request.assigned_to
        if data.status in {HandoffStatus.IN_PROGRESS, HandoffStatus.RESOLVED}:
            assignee = assignee or actor.user_id
            if not self.repository.can_handle(assignee):
                raise ConflictError("Assignee must have the STAFF or ADMIN role.", "invalid_assignee")
        previous_status = request.status
        request.assigned_to = assignee
        request.status = data.status
        request.resolved_at = datetime.now(timezone.utc) if data.status == HandoffStatus.RESOLVED else None
        self.session.add(
            AuditLog(
                actor_user_id=actor.user_id,
                action="HANDOFF_UPDATED",
                entity_type="handoff_request",
                entity_id=request.id,
                audit_metadata={
                    "previous_status": previous_status.value,
                    "new_status": request.status.value,
                    "assigned_to": str(assignee) if assignee else None,
                },
            )
        )
        self.session.commit()
        self.session.refresh(request)
        return request
