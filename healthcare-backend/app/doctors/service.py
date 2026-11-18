"""Doctor master-data rules."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.context import ActorContext
from app.auth.passwords import hash_password
from app.core.errors import ConflictError, NotFoundError
from app.doctors.repository import DoctorRepository
from app.doctors.schemas import DoctorCreate, DoctorProvisionCreate, DoctorUpdate
from app.models.care import Doctor, Specialty
from app.models.enums import UserStatus
from app.models.identity import User
from app.models.operations import AuditLog
from app.users.repository import UserRepository


class DoctorService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DoctorRepository(session)
        self.users = UserRepository(session)

    def list(self, specialty_id: UUID | None = None, active_only: bool | None = None) -> list[Doctor]:
        return self.repository.list(specialty_id, active_only)

    def get(self, doctor_id: UUID) -> Doctor:
        doctor = self.repository.get(doctor_id)
        if doctor is None:
            raise NotFoundError("Doctor was not found.", "doctor_not_found")
        return doctor

    def list_candidates(self, actor: ActorContext) -> list[User]:
        actor.require_any_role("ADMIN")
        return self.repository.list_candidates()

    def _validate_references(self, user_id: UUID, specialty_id: UUID) -> None:
        user = self.repository.get_user(user_id)
        if user is None:
            raise NotFoundError("Doctor user was not found.", "user_not_found")
        if user.status != UserStatus.ACTIVE:
            raise ConflictError("An inactive user cannot be assigned.", "doctor_user_inactive")
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

    def provision(self, data: DoctorProvisionCreate, actor: ActorContext) -> Doctor:
        actor.require_any_role("ADMIN")
        if self.users.get_by_email(data.email) is not None:
            raise ConflictError("An account with this email already exists.", "email_exists")
        doctor_role = self.users.get_role("DOCTOR")
        if doctor_role is None:
            raise ConflictError("The DOCTOR role is not available.", "doctor_role_unavailable")
        specialty = self.session.get(Specialty, data.specialty_id)
        if specialty is None:
            raise NotFoundError("Specialty was not found.", "specialty_not_found")
        if not specialty.is_active:
            raise ConflictError("An inactive specialty cannot be assigned.", "specialty_inactive")

        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            phone=data.phone,
            date_of_birth=data.date_of_birth,
            gender=data.gender,
            status=UserStatus.ACTIVE,
        )
        self.users.add(user)
        try:
            self.session.flush()
            self.users.assign_role(user, doctor_role, assigned_by=actor.user_id)
            doctor = Doctor(
                user_id=user.id,
                specialty_id=data.specialty_id,
                license_number=data.license_number.strip().upper(),
                biography=data.biography,
            )
            self.repository.add(doctor)
            self.session.flush()
            self.session.add(
                AuditLog(
                    actor_user_id=actor.user_id,
                    action="DOCTOR_PROVISIONED",
                    entity_type="DOCTOR",
                    entity_id=doctor.id,
                    audit_metadata={"user_id": str(user.id), "specialty_id": str(data.specialty_id)},
                )
            )
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError(
                "The email or doctor license number already exists.", "doctor_provision_conflict"
            ) from exc
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
