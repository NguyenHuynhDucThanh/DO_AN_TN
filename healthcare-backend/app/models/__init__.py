"""Phase 2 SQLAlchemy model registry."""

from app.models.care import Appointment, Doctor, DoctorSchedule, ScheduleSlot, Specialty
from app.models.identity import RefreshSession, Role, User, UserRole
from app.models.knowledge import EMBEDDING_DIMENSION, Document, DocumentChunk
from app.models.medical_record import MedicalRecord
from app.models.operations import AuditLog, HandoffRequest

__all__ = [
    "Appointment", "AuditLog", "Doctor", "DoctorSchedule", "Document", "DocumentChunk",
    "EMBEDDING_DIMENSION", "HandoffRequest", "MedicalRecord", "RefreshSession", "Role",
    "ScheduleSlot", "Specialty", "User", "UserRole",
]
