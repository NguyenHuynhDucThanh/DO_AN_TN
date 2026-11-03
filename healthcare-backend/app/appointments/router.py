"""Appointment REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.appointments.schemas import AppointmentCancel, AppointmentCreate, AppointmentOutcome, AppointmentRead
from app.appointments.service import AppointmentService
from app.auth.context import ActorContext
from app.auth.dependencies import get_current_actor
from app.core.database import get_db

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("", response_model=list[AppointmentRead])
def list_appointments(
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return AppointmentService(db).list(actor)


@router.get("/{appointment_id}", response_model=AppointmentRead)
def get_appointment(
    appointment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return AppointmentService(db).get(appointment_id, actor)


@router.post("", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
def create_appointment(
    data: AppointmentCreate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return AppointmentService(db).create(data, actor)


@router.post("/{appointment_id}/cancel", response_model=AppointmentRead)
def cancel_appointment(
    appointment_id: UUID,
    data: AppointmentCancel,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return AppointmentService(db).cancel(appointment_id, data, actor)


@router.post("/{appointment_id}/outcome", response_model=AppointmentRead)
def set_appointment_outcome(
    appointment_id: UUID,
    data: AppointmentOutcome,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return AppointmentService(db).set_outcome(appointment_id, data, actor)
