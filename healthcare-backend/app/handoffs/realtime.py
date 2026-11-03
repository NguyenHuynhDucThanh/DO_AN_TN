"""Best-effort in-process WebSocket notifications for durable handoff records."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import WebSocket

from app.models.operations import HandoffRequest

logger = logging.getLogger(__name__)


def handoff_event_payload(event_type: str, request: HandoffRequest) -> dict[str, Any]:
    """Return metadata only; ticket details remain authoritative in the REST API."""
    return {
        "type": event_type,
        "handoff": {
            "id": str(request.id),
            "requester_id": str(request.requester_id),
            "assigned_to": str(request.assigned_to) if request.assigned_to else None,
            "source": request.source,
            "priority": request.priority.value,
            "status": request.status.value,
            "created_at": _isoformat(request.created_at),
            "updated_at": _isoformat(request.updated_at),
        },
    }


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


class HandoffConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[UUID, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, actor_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.setdefault(actor_id, set()).add(websocket)

    async def disconnect(self, actor_id: UUID, websocket: WebSocket) -> None:
        async with self._lock:
            connections = self._connections.get(actor_id)
            if connections is None:
                return
            connections.discard(websocket)
            if not connections:
                self._connections.pop(actor_id, None)

    async def publish(self, event: dict[str, Any]) -> None:
        async with self._lock:
            targets = [item for group in self._connections.values() for item in group]
        failed: list[WebSocket] = []
        for websocket in targets:
            try:
                await websocket.send_json(event)
            except Exception:
                failed.append(websocket)
        if failed:
            async with self._lock:
                for actor_id, connections in list(self._connections.items()):
                    connections.difference_update(failed)
                    if not connections:
                        self._connections.pop(actor_id, None)
            logger.info("Removed %d disconnected handoff WebSocket client(s)", len(failed))

    async def publish_handoff(self, event_type: str, request: HandoffRequest) -> None:
        try:
            await self.publish(handoff_event_payload(event_type, request))
        except Exception:
            # PostgreSQL and REST remain authoritative if realtime delivery fails.
            logger.warning("Handoff WebSocket publish failed", exc_info=True)

    @property
    def connection_count(self) -> int:
        return sum(len(group) for group in self._connections.values())


handoff_connections = HandoffConnectionManager()
