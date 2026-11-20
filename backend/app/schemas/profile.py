from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from app.schemas.common import normalize_optional_text, validate_iana_timezone


class ProfileResponse(BaseModel):
    id: UUID
    display_name: str
    timezone: str
    active_priority_title: str | None = None
    active_priority_task_id: UUID | None = None
    active_priority_project_id: UUID | None = None
    preferences: dict[str, Any] = Field(default_factory=dict)
    ai_instructions: str | None = None
    created_at: datetime
    updated_at: datetime


class ProfileUpdate(BaseModel):
    display_name: str | None = None
    timezone: str | None = None
    active_priority_title: str | None = None
    active_priority_task_id: UUID | None = None
    active_priority_project_id: UUID | None = None
    preferences: dict[str, Any] | None = None
    ai_instructions: str | None = None

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Le nom d’affichage ne peut pas être null.")
        cleaned = value.strip()
        if not cleaned or len(cleaned) > 100:
            raise ValueError("Le nom d’affichage doit contenir entre 1 et 100 caractères.")
        return cleaned

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Le fuseau horaire ne peut pas être null.")
        return validate_iana_timezone(value)

    @field_validator("active_priority_title")
    @classmethod
    def validate_active_priority_title(cls, value: str | None) -> str | None:
        cleaned = normalize_optional_text(value, 200)
        if cleaned is not None and len(cleaned) < 2:
            raise ValueError("La priorité principale doit contenir au moins 2 caractères.")
        return cleaned

    @field_validator("ai_instructions")
    @classmethod
    def validate_ai_instructions(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 2000)
