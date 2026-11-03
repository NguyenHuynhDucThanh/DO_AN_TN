"""Basic MedicalRecord API contracts."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MedicalRecordCreate(BaseModel):
    appointment_id: UUID
    symptoms: str = Field(min_length=1, max_length=10000)
    clinical_notes: str = Field(min_length=1, max_length=20000)
    doctor_conclusion: str = Field(min_length=1, max_length=10000)
    follow_up_instructions: str = Field(min_length=1, max_length=10000)


class MedicalRecordUpdate(BaseModel):
    symptoms: str | None = Field(default=None, min_length=1, max_length=10000)
    clinical_notes: str | None = Field(default=None, min_length=1, max_length=20000)
    doctor_conclusion: str | None = Field(default=None, min_length=1, max_length=10000)
    follow_up_instructions: str | None = Field(default=None, min_length=1, max_length=10000)

    @model_validator(mode="after")
    def require_a_change(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied")
        return self


class MedicalRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    appointment_id: UUID
    symptoms: str
    clinical_notes: str
    doctor_conclusion: str
    follow_up_instructions: str
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime
