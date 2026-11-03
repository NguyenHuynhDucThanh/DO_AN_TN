"""Specialty REST endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.context import ActorContext
from app.auth.dependencies import get_current_actor
from app.core.database import get_db
from app.specialties.schemas import SpecialtyCreate, SpecialtyRead, SpecialtyStatusUpdate, SpecialtyUpdate
from app.specialties.service import SpecialtyService

router = APIRouter(prefix="/specialties", tags=["Specialties"])


@router.get("", response_model=list[SpecialtyRead])
def list_specialties(
    db: Annotated[Session, Depends(get_db)], active: Annotated[bool | None, Query()] = None
):
    return SpecialtyService(db).list(active)


@router.get("/{specialty_id}", response_model=SpecialtyRead)
def get_specialty(specialty_id: UUID, db: Annotated[Session, Depends(get_db)]):
    return SpecialtyService(db).get(specialty_id)


@router.post("", response_model=SpecialtyRead, status_code=status.HTTP_201_CREATED)
def create_specialty(
    data: SpecialtyCreate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return SpecialtyService(db).create(data, actor)


@router.patch("/{specialty_id}", response_model=SpecialtyRead)
def update_specialty(
    specialty_id: UUID,
    data: SpecialtyUpdate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return SpecialtyService(db).update(specialty_id, data, actor)


@router.patch("/{specialty_id}/status", response_model=SpecialtyRead)
def update_specialty_status(
    specialty_id: UUID,
    data: SpecialtyStatusUpdate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return SpecialtyService(db).set_status(specialty_id, data, actor)
