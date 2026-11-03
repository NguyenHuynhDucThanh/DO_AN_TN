"""Versioned API composition and database readiness endpoint."""

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.auth.router import router as auth_router
from app.appointments.router import router as appointments_router
from app.doctors.router import router as doctors_router
from app.documents.router import router as documents_router
from app.handoffs.router import router as handoffs_router
from app.medical_records.router import router as medical_records_router
from app.schedules.router import router as schedules_router
from app.specialties.router import router as specialties_router
from app.users.router import router as users_router
from app.ai.router import router as ai_router
from app.voice.router import router as voice_router

logger = logging.getLogger(__name__)
router = APIRouter()
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(specialties_router)
router.include_router(doctors_router)
router.include_router(schedules_router)
router.include_router(appointments_router)
router.include_router(medical_records_router)
router.include_router(documents_router)
router.include_router(handoffs_router)
router.include_router(ai_router)
router.include_router(voice_router)


class HealthResponse(BaseModel):
    status: Literal["ok", "unavailable"]
    application: str
    environment: str


@router.get(
    "/health",
    tags=["Health"],
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse, "description": "Database or pgvector not ready"}},
)
def health(db: Annotated[Session, Depends(get_db)]) -> HealthResponse | JSONResponse:
    settings = get_settings()
    payload = HealthResponse(
        status="ok", application="healthcare-backend", environment=settings.app_env
    )
    try:
        db.execute(text("SELECT 1"))
        extension = db.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        ).scalar_one_or_none()
        if extension != "vector":
            payload.status = "unavailable"
    except SQLAlchemyError:
        # Connection errors may contain sensitive DSN/user data; do not echo them.
        logger.warning("Database readiness check failed")
        payload.status = "unavailable"

    if payload.status == "unavailable":
        return JSONResponse(status_code=503, content=payload.model_dump())
    return payload
