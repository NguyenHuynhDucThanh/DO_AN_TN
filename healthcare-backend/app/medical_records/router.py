"""Protected MedicalRecord endpoints; no DELETE endpoint by design."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.context import ActorContext
from app.auth.dependencies import get_current_actor
from app.core.database import get_db
from app.medical_records.schemas import MedicalRecordCreate, MedicalRecordRead, MedicalRecordUpdate
from app.medical_records.service import MedicalRecordService

router = APIRouter(prefix="/medical-records", tags=["Medical Records"])


@router.post("", response_model=MedicalRecordRead, status_code=status.HTTP_201_CREATED)
def create_medical_record(
    data: MedicalRecordCreate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return MedicalRecordService(db).create_medical_record(data, actor)


@router.get("/me/history", response_model=list[MedicalRecordRead])
def list_my_medical_history(
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return MedicalRecordService(db).list_patient_medical_history(actor.user_id, actor)


@router.get("/by-appointment/{appointment_id}", response_model=MedicalRecordRead)
def get_medical_record_by_appointment(
    appointment_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return MedicalRecordService(db).get_by_appointment(appointment_id, actor)


@router.get("/{record_id}", response_model=MedicalRecordRead)
def get_medical_record(
    record_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return MedicalRecordService(db).get_medical_record(record_id, actor)


@router.patch("/{record_id}", response_model=MedicalRecordRead)
def update_medical_record(
    record_id: UUID,
    data: MedicalRecordUpdate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[ActorContext, Depends(get_current_actor)],
):
    return MedicalRecordService(db).update_medical_record(record_id, data, actor)
