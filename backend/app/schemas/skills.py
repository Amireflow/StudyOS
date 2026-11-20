from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, field_validator
from app.schemas.common import (
    SkillEvidenceType,
    UtcDatetime,
    normalize_optional_text,
    validate_optional_http_url,
)


def _validate_skill_level(value: int) -> int:
    if value < 0 or value > 5:
        raise ValueError("Le niveau de compétence doit être compris entre 0 et 5.")
    return value


class SkillCreate(BaseModel):
    name: str
    domain: str
    description: str | None = None
    current_level: int = 0
    target_level: int | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 120:
            raise ValueError("Le nom doit contenir entre 2 et 120 caractères.")
        return cleaned

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 80:
            raise ValueError("Le domaine doit contenir entre 2 et 80 caractères.")
        return cleaned

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 1000)

    @field_validator("current_level")
    @classmethod
    def validate_current_level(cls, value: int) -> int:
        return _validate_skill_level(value)

    @field_validator("target_level")
    @classmethod
    def validate_target_level(cls, value: int | None) -> int | None:
        if value is None:
            return None
        return _validate_skill_level(value)


class SkillUpdate(BaseModel):
    name: str | None = None
    domain: str | None = None
    description: str | None = None
    current_level: int | None = None
    target_level: int | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Le nom ne peut pas être null.")
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 120:
            raise ValueError("Le nom doit contenir entre 2 et 120 caractères.")
        return cleaned

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Le domaine ne peut pas être null.")
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 80:
            raise ValueError("Le domaine doit contenir entre 2 et 80 caractères.")
        return cleaned

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 1000)

    @field_validator("current_level")
    @classmethod
    def validate_current_level(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("Le niveau actuel ne peut pas être null.")
        return _validate_skill_level(value)

    @field_validator("target_level")
    @classmethod
    def validate_target_level(cls, value: int | None) -> int | None:
        if value is None:
            return None
        return _validate_skill_level(value)


class SkillResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    domain: str
    description: str | None = None
    current_level: int
    target_level: int | None = None
    last_assessed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SkillEvidenceCreate(BaseModel):
    type: SkillEvidenceType = SkillEvidenceType.exercise
    description: str
    reference_url: str | None = None
    result: str | None = None
    observed_at: UtcDatetime | None = None

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 1000:
            raise ValueError("La description de la preuve doit contenir entre 2 et 1000 caractères.")
        return cleaned

    @field_validator("reference_url")
    @classmethod
    def validate_reference_url(cls, value: str | None) -> str | None:
        return validate_optional_http_url(value)

    @field_validator("result")
    @classmethod
    def validate_result(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 200)


class SkillEvidenceUpdate(BaseModel):
    type: SkillEvidenceType | None = None
    description: str | None = None
    reference_url: str | None = None
    result: str | None = None
    observed_at: UtcDatetime | None = None

    @field_validator("type")
    @classmethod
    def reject_null_type(cls, value: SkillEvidenceType | None) -> SkillEvidenceType:
        if value is None:
            raise ValueError("Le type de preuve ne peut pas être null.")
        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("La description de la preuve ne peut pas être null.")
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 1000:
            raise ValueError("La description de la preuve doit contenir entre 2 et 1000 caractères.")
        return cleaned

    @field_validator("reference_url")
    @classmethod
    def validate_reference_url(cls, value: str | None) -> str | None:
        return validate_optional_http_url(value)

    @field_validator("result")
    @classmethod
    def validate_result(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 200)

    @field_validator("observed_at")
    @classmethod
    def reject_null_observed_at(cls, value: UtcDatetime | None) -> UtcDatetime:
        if value is None:
            raise ValueError("La date d’observation ne peut pas être null.")
        return value


class SkillEvidenceResponse(BaseModel):
    id: UUID
    user_id: UUID
    skill_id: UUID
    type: SkillEvidenceType
    description: str
    reference_url: str | None = None
    result: str | None = None
    observed_at: datetime
    created_at: datetime
    updated_at: datetime
