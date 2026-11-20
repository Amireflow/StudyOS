from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, field_validator
from app.schemas.common import (
    LearningStatus,
    normalize_optional_text,
    validate_optional_http_url,
)


def _validate_title_required(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) < 2 or len(cleaned) > 140:
        raise ValueError("Le titre doit contenir entre 2 et 140 caractères.")
    return cleaned


def _validate_goal_required(value: str) -> str:
    cleaned = value.strip()
    if len(cleaned) < 2 or len(cleaned) > 300:
        raise ValueError("L’objectif doit contenir entre 2 et 300 caractères.")
    return cleaned


class LearningPathCreate(BaseModel):
    title: str
    description: str | None = None
    goal: str
    status: LearningStatus = LearningStatus.not_started

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _validate_title_required(value)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 1000)

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, value: str) -> str:
        return _validate_goal_required(value)


class LearningPathUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    goal: str | None = None
    status: LearningStatus | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Le titre ne peut pas être null.")
        return _validate_title_required(value)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 1000)

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("L’objectif ne peut pas être null.")
        return _validate_goal_required(value)

    @field_validator("status")
    @classmethod
    def reject_null_status(cls, value: LearningStatus | None) -> LearningStatus:
        if value is None:
            raise ValueError("Le statut ne peut pas être null.")
        return value


class LearningPathResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    description: str | None = None
    status: LearningStatus
    goal: str
    created_at: datetime
    updated_at: datetime


class LearningModuleCreate(BaseModel):
    path_id: UUID
    title: str
    description: str | None = None
    position: int = 0
    status: LearningStatus = LearningStatus.not_started

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _validate_title_required(value)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 1000)

    @field_validator("position")
    @classmethod
    def validate_position(cls, value: int) -> int:
        if value < 0 or value > 1000:
            raise ValueError("La position doit être comprise entre 0 et 1000.")
        return value


class LearningModuleUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    position: int | None = None
    status: LearningStatus | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Le titre ne peut pas être null.")
        return _validate_title_required(value)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 1000)

    @field_validator("position")
    @classmethod
    def validate_position(cls, value: int | None) -> int:
        if value is None or value < 0 or value > 1000:
            raise ValueError("La position doit être comprise entre 0 et 1000.")
        return value

    @field_validator("status")
    @classmethod
    def reject_null_status(cls, value: LearningStatus | None) -> LearningStatus:
        if value is None:
            raise ValueError("Le statut ne peut pas être null.")
        return value


class LearningModuleResponse(BaseModel):
    id: UUID
    user_id: UUID
    path_id: UUID
    title: str
    description: str | None = None
    position: int
    status: LearningStatus
    created_at: datetime
    updated_at: datetime


class LessonCreate(BaseModel):
    module_id: UUID
    title: str
    content: str | None = None
    resource_url: str | None = None
    position: int = 0
    status: LearningStatus = LearningStatus.not_started

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _validate_title_required(value)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 4000)

    @field_validator("resource_url")
    @classmethod
    def validate_resource_url(cls, value: str | None) -> str | None:
        return validate_optional_http_url(value)

    @field_validator("position")
    @classmethod
    def validate_position(cls, value: int) -> int:
        if value < 0 or value > 1000:
            raise ValueError("La position doit être comprise entre 0 et 1000.")
        return value


class LessonUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    resource_url: str | None = None
    position: int | None = None
    status: LearningStatus | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Le titre ne peut pas être null.")
        return _validate_title_required(value)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 4000)

    @field_validator("resource_url")
    @classmethod
    def validate_resource_url(cls, value: str | None) -> str | None:
        return validate_optional_http_url(value)

    @field_validator("position")
    @classmethod
    def validate_position(cls, value: int | None) -> int:
        if value is None or value < 0 or value > 1000:
            raise ValueError("La position doit être comprise entre 0 et 1000.")
        return value

    @field_validator("status")
    @classmethod
    def reject_null_status(cls, value: LearningStatus | None) -> LearningStatus:
        if value is None:
            raise ValueError("Le statut ne peut pas être null.")
        return value


class LessonResponse(BaseModel):
    id: UUID
    user_id: UUID
    module_id: UUID
    title: str
    content: str | None = None
    resource_url: str | None = None
    position: int
    status: LearningStatus
    created_at: datetime
    updated_at: datetime


class LearningOverviewResponse(BaseModel):
    paths: list[LearningPathResponse]
    modules: list[LearningModuleResponse]
    lessons: list[LessonResponse]
