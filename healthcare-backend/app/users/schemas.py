"""Current-user profile contracts."""

from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.auth.schemas import _normalize_phone
from app.models.enums import Gender


class UserProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = None
    date_of_birth: date | None = None
    gender: Gender | None = None

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        return _normalize_phone(value) if value is not None else None
