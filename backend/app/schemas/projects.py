from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator
from app.schemas.common import (
    ProjectStatus,
    TaskPriority,
    UtcDatetime,
    normalize_optional_text,
)


def _normalize_deliverables(value: list[str] | None) -> list[str] | None:
    if value is None:
        return None
    cleaned: list[str] = []
    for item in value:
        trimmed = item.strip()
        if trimmed:
            if len(trimmed) > 160:
                raise ValueError("Chaque livrable doit contenir au plus 160 caractères.")
            cleaned.append(trimmed)
    if len(cleaned) > 30:
        raise ValueError("Un projet ne peut pas contenir plus de 30 livrables.")
    return cleaned or None


class ProjectCreate(BaseModel):
    name: str
    category: str = "project"
    description: str | None = None
    goal: str
    status: ProjectStatus = ProjectStatus.planned
    priority: TaskPriority = TaskPriority.normal
    motivation: str | None = None
    start_date: UtcDatetime | None = None
    weekly_target_minutes: int = Field(default=180, ge=0, le=3000)
    next_action: str = ""
    steps: list[dict[str, Any]] = Field(default_factory=list)
    deliverables: list[str] | None = None
    success_criteria: list[str] = Field(default_factory=list)
    target_date: UtcDatetime | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 140:
            raise ValueError("Le nom du projet doit contenir entre 2 et 140 caractères.")
        return cleaned

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 2000)

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 300:
            raise ValueError("L’objectif du projet doit contenir entre 2 et 300 caractères.")
        return cleaned

    @field_validator("next_action")
    @classmethod
    def validate_next_action(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) > 240:
            raise ValueError("La prochaine action ne doit pas dépasser 240 caractères.")
        return cleaned

    @field_validator("deliverables")
    @classmethod
    def validate_deliverables(cls, value: list[str] | None) -> list[str] | None:
        return _normalize_deliverables(value)

    @model_validator(mode="after")
    def require_next_action_when_active(self) -> "ProjectCreate":
        if self.status == ProjectStatus.active and len(self.next_action) < 2:
            raise ValueError(
                "Une prochaine action concrète (min. 2 caractères) est obligatoire pour un projet actif."
            )
        return self


class ProjectUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    goal: str | None = None
    status: ProjectStatus | None = None
    priority: TaskPriority | None = None
    motivation: str | None = None
    start_date: UtcDatetime | None = None
    weekly_target_minutes: int | None = Field(default=None, ge=0, le=3000)
    next_action: str | None = None
    steps: list[dict[str, Any]] | None = None
    deliverables: list[str] | None = None
    success_criteria: list[str] | None = None
    target_date: UtcDatetime | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Le nom du projet ne peut pas être null.")
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 140:
            raise ValueError("Le nom du projet doit contenir entre 2 et 140 caractères.")
        return cleaned

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 2000)

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("L’objectif du projet ne peut pas être null.")
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 300:
            raise ValueError("L’objectif du projet doit contenir entre 2 et 300 caractères.")
        return cleaned

    @field_validator("status", "priority")
    @classmethod
    def reject_null_enum(cls, value: ProjectStatus | TaskPriority | None) -> ProjectStatus | TaskPriority:
        if value is None:
            raise ValueError("Ce champ ne peut pas être null.")
        return value

    @field_validator("next_action")
    @classmethod
    def validate_next_action(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("La prochaine action ne peut pas être null.")
        cleaned = value.strip()
        if len(cleaned) > 240:
            raise ValueError("La prochaine action ne doit pas dépasser 240 caractères.")
        return cleaned

    @field_validator("deliverables")
    @classmethod
    def validate_deliverables(cls, value: list[str] | None) -> list[str] | None:
        return _normalize_deliverables(value)


class ProjectResponse(BaseModel):
    id: UUID
    user_id: UUID
    category: str = "project"
    name: str
    description: str | None = None
    goal: str
    status: ProjectStatus
    priority: TaskPriority
    motivation: str | None = None
    start_date: datetime | None = None
    weekly_target_minutes: int = 180
    next_action: str
    steps: list[dict[str, Any]] = Field(default_factory=list)
    deliverables: list[str] | None = None
    success_criteria: list[str] = Field(default_factory=list)
    progress_history: list[dict[str, Any]] = Field(default_factory=list)
    target_date: datetime | None = None
    created_at: datetime
    updated_at: datetime
