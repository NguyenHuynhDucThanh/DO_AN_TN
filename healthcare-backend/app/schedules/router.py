"""Schedule and slot REST endpoints."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.context import ActorContext
from app.auth.dependencies import get_current_actor
from app.core.database import get_db
from app.schedules.schemas import ScheduleCreate, ScheduleRead, ScheduleUpdate, SlotRead, SlotStatusUpdate
from app.schedules.service import ScheduleService

router = APIRouter(prefix="/schedules", tags=["Schedules"])


@router.get("", response_model=list[ScheduleRead])
def list_schedules(
    db: Annotated[Session, Depends(get_db)], doctor_id: Annotated[UUID | None, Query()] = None
):
    return ScheduleService(db).list(doctor_id)


@router.get("/available-slots", response_model=list[SlotRead])
def list_available_slots(
    from_at: Annotated[datetime, Query()],
    to_at: Annotated[datetime, Query()],
    db: Annotated[Session, Depends(get_db)],
    doctor_id: Annotated[UUID | None, Query()] = None,
    specialty_id: Annotated[UUID | None, Query()] = None,
):
    return ScheduleService(db).available_slots(from_at, to_at, doctor_id, specialty_id)


@router.get("/{schedule_id}", response_model=ScheduleRead)
def get_schedule(schedule_id: UUID, db: Annotated[Session, Depends(get_db)]):
    return ScheduleService(db).get(schedule_id)


@router.post("", response_model=ScheduleRead, status_code=status.HTTP_201_CREATED)
def create_schedule(
    data: ScheduleCreate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return ScheduleService(db).create(data, actor)


@router.patch("/{schedule_id}", response_model=ScheduleRead)
def update_schedule(
    schedule_id: UUID,
    data: ScheduleUpdate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return ScheduleService(db).update(schedule_id, data, actor)


@router.post("/{schedule_id}/slots/generate", response_model=list[SlotRead], status_code=status.HTTP_201_CREATED)
def generate_slots(
    schedule_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return ScheduleService(db).generate_slots(schedule_id, actor)


@router.patch("/slots/{slot_id}/status", response_model=SlotRead)
def set_slot_status(
    slot_id: UUID,
    data: SlotStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return ScheduleService(db).set_slot_status(slot_id, data, actor)
