"""Doctor master-data rules."""

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.context import ActorContext
from app.core.errors import ConflictError, NotFoundError
from app.doctors.repository import DoctorRepository
from app.doctors.schemas import DoctorCreate, DoctorUpdate
from app.models.care import Doctor, Specialty


class DoctorService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DoctorRepository(session)

    def list(self, specialty_id: UUID | None = None, active_only: bool | None = None) -> list[Doctor]:
        return self.repository.list(specialty_id, active_only)

    def get(self, doctor_id: UUID) -> Doctor:
        doctor = self.repository.get(doctor_id)
        if doctor is None:
            raise NotFoundError("Doctor was not found.", "doctor_not_found")
        return doctor

    def _validate_references(self, user_id: UUID, specialty_id: UUID) -> None:
        if not self.repository.user_exists(user_id):
            raise NotFoundError("Doctor user was not found.", "user_not_found")
        if not self.repository.user_has_doctor_role(user_id):
            raise ConflictError("The selected user does not have the DOCTOR role.", "doctor_role_required")
        specialty = self.session.get(Specialty, specialty_id)
        if specialty is None:
            raise NotFoundError("Specialty was not found.", "specialty_not_found")
        if not specialty.is_active:
            raise ConflictError("An inactive specialty cannot be assigned.", "specialty_inactive")

    def create(self, data: DoctorCreate, actor: ActorContext) -> Doctor:
        actor.require_any_role("ADMIN")
        self._validate_references(data.user_id, data.specialty_id)
        doctor = Doctor(**data.model_dump())
        doctor.license_number = doctor.license_number.strip().upper()
        self.repository.add(doctor)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("Doctor user or license number already exists.", "doctor_exists") from exc
        return self.get(doctor.id)

    def update(self, doctor_id: UUID, data: DoctorUpdate, actor: ActorContext) -> Doctor:
        actor.require_any_role("ADMIN")
        doctor = self.get(doctor_id)
        changes = data.model_dump(exclude_unset=True)
        if changes.get("specialty_id") is not None:
            self._validate_references(doctor.user_id, changes["specialty_id"])
        for field, value in changes.items():
            if field == "license_number" and value is not None:
                value = value.strip().upper()
            setattr(doctor, field, value)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("Doctor license number already exists.", "doctor_exists") from exc
        return self.get(doctor.id)
