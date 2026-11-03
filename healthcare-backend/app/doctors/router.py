"""Doctor REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.context import ActorContext
from app.auth.dependencies import get_current_actor
from app.core.database import get_db
from app.doctors.schemas import DoctorCreate, DoctorRead, DoctorUpdate
from app.doctors.service import DoctorService

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.get("", response_model=list[DoctorRead])
def list_doctors(
    db: Annotated[Session, Depends(get_db)],
    specialty_id: Annotated[UUID | None, Query()] = None,
    active: Annotated[bool | None, Query()] = None,
):
    return DoctorService(db).list(specialty_id, active)


@router.get("/{doctor_id}", response_model=DoctorRead)
def get_doctor(doctor_id: UUID, db: Annotated[Session, Depends(get_db)]):
    return DoctorService(db).get(doctor_id)


@router.post("", response_model=DoctorRead, status_code=status.HTTP_201_CREATED)
def create_doctor(
    data: DoctorCreate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return DoctorService(db).create(data, actor)


@router.patch("/{doctor_id}", response_model=DoctorRead)
def update_doctor(
    doctor_id: UUID,
    data: DoctorUpdate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return DoctorService(db).update(doctor_id, data, actor)
