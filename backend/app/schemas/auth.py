import re
from typing import Literal
from pydantic import BaseModel, field_validator
from app.schemas.profile import ProfileResponse

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LocalLoginRequest(BaseModel):
    email: str = "etudiant@amireflow.local"
    display_name: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not _EMAIL_PATTERN.match(cleaned):
            raise ValueError("Adresse e-mail invalide.")
        return cleaned

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


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    profile: ProfileResponse
