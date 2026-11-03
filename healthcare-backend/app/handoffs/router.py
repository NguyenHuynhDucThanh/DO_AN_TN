"""Durable Handoff REST endpoints plus a best-effort realtime notification layer."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.auth.context import ActorContext
from app.auth.dependencies import get_current_actor, get_websocket_actor
from app.core.errors import ApplicationError
from app.core.database import get_db
from app.handoffs.schemas import HandoffCreate, HandoffRead, HandoffUpdate
from app.handoffs.service import HandoffService
from app.handoffs.realtime import handoff_connections

router = APIRouter(prefix="/handoffs", tags=["Handoffs"])


@router.get("", response_model=list[HandoffRead])
def list_handoffs(
    db: Annotated[Session, Depends(get_db)], actor: Annotated[ActorContext, Depends(get_current_actor)]
):
    return HandoffService(db).list(actor)


@router.get("/{request_id}", response_model=HandoffRead)
def get_handoff(
    request_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return HandoffService(db).get(request_id, actor)


@router.post("", response_model=HandoffRead, status_code=status.HTTP_201_CREATED)
async def create_handoff(
    data: HandoffCreate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    request = HandoffService(db).create(data, actor)
    await handoff_connections.publish_handoff("handoff.created", request)
    return request


@router.patch("/{request_id}", response_model=HandoffRead)
async def update_handoff(
    request_id: UUID,
    data: HandoffUpdate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    request = HandoffService(db).update(request_id, data, actor)
    await handoff_connections.publish_handoff("handoff.updated", request)
    return request


@router.websocket("/ws")
async def handoff_websocket(websocket: WebSocket, db: Session = Depends(get_db)) -> None:
    try:
        actor = get_websocket_actor(websocket, db)
        actor.require_any_role("STAFF", "ADMIN")
    except ApplicationError as exc:
        await websocket.close(code=4403 if exc.status_code == 403 else 4401)
        return
    await handoff_connections.connect(actor.user_id, websocket)
    try:
        await websocket.send_json({"type": "handoff.connected"})
        while True:
            # The server has no client-controlled state; receiving keeps disconnect detection simple.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await handoff_connections.disconnect(actor.user_id, websocket)
