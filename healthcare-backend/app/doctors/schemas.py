"""Doctor API contracts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.auth.schemas import RegisterRequest


class DoctorCreate(BaseModel):
    user_id: UUID
    specialty_id: UUID
    license_number: str = Field(min_length=2, max_length=50)
    biography: str | None = Field(default=None, max_length=5000)


class DoctorProvisionCreate(RegisterRequest):
    specialty_id: UUID
    license_number: str = Field(min_length=2, max_length=50)
    biography: str | None = Field(default=None, max_length=5000)


class DoctorUpdate(BaseModel):
    specialty_id: UUID | None = None
    license_number: str | None = Field(default=None, min_length=2, max_length=50)
    biography: str | None = Field(default=None, max_length=5000)
    is_active: bool | None = None


class DoctorUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    full_name: str
    email: str
    phone: str | None


class DoctorCandidateRead(DoctorUserRead):
    pass


class DoctorSpecialtyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str


class DoctorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    specialty_id: UUID
    license_number: str
    biography: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    user: DoctorUserRead
    specialty: DoctorSpecialtyRead
