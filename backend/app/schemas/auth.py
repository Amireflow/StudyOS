from datetime import datetime
import re
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, field_validator
from app.core.security import validate_password_policy
from app.schemas.common import validate_iana_timezone
from app.schemas.profile import ProfileResponse

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email_str(value: str) -> str:
    cleaned = value.strip().lower()
    if len(cleaned) > 255 or not _EMAIL_PATTERN.match(cleaned):
        raise ValueError("Adresse e-mail invalide.")
    return cleaned


class LocalLoginRequest(BaseModel):
    email: str = "etudiant@amireflow.local"
    display_name: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _validate_email_str(value)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if len(cleaned) < 2 or len(cleaned) > 100:
            raise ValueError("Le nom d’affichage doit contenir entre 2 et 100 caractères.")
        return cleaned


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str
    timezone: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _validate_email_str(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_policy(value)

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 100:
            raise ValueError("Le nom d’affichage doit contenir entre 2 et 100 caractères.")
        return cleaned

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        return validate_iana_timezone(cleaned)


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _validate_email_str(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 1 or len(value) > 128:
            raise ValueError("Le mot de passe est requis.")
        return value


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @field_validator("current_password")
    @classmethod
    def validate_current_password(cls, value: str) -> str:
        if len(value) < 1 or len(value) > 128:
            raise ValueError("Le mot de passe actuel est requis.")
        return value

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return validate_password_policy(value)


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    email: str | None = None
    profile: ProfileResponse


class AuthAccountResponse(BaseModel):
    id: UUID
    email: str | None = None
    auth_provider: Literal["password", "external"]
    has_password_account: bool
    email_verified: bool = False
    can_change_password: bool = False
    password_reset_mode: Literal["external_provider", "unavailable_no_mailer"] = "unavailable_no_mailer"
    last_login_at: datetime | None = None
    created_at: datetime
    profile: ProfileResponse
