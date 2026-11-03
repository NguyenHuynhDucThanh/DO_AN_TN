"""Authentication and current-user API contracts."""

from datetime import date, datetime
import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import Gender, UserStatus

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if len(normalized) > 320 or not EMAIL_PATTERN.fullmatch(normalized):
        raise ValueError("Email is invalid")
    return normalized


def _validate_password_strength(password: str) -> str:
    if not any(character.isalpha() for character in password) or not any(
        character.isdigit() for character in password
    ):
        raise ValueError("Password must contain at least one letter and one number")
    return password


def _normalize_phone(phone: str) -> str:
    normalized = phone.strip()
    if not 8 <= len(normalized) <= 20:
        raise ValueError("Phone must contain between 8 and 20 characters")
    if any(character not in "+-(). 0123456789" for character in normalized):
        raise ValueError("Phone contains unsupported characters")
    return normalized


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=150)
    phone: str
    date_of_birth: date | None = None
    gender: Gender | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_password_strength(value)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return _normalize_phone(value)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _normalize_email(value)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    phone: str | None
    date_of_birth: date | None
    gender: Gender | None
    status: UserStatus
    roles: list[str]
    created_at: datetime
    updated_at: datetime


class SessionResponse(BaseModel):
    user: UserRead
