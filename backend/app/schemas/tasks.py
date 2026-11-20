from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, field_validator
from app.schemas.common import (
    TaskPriority,
    TaskSource,
    TaskStatus,
    UtcDatetime,
    normalize_optional_text,
)


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    status: TaskStatus = TaskStatus.todo
    priority: TaskPriority = TaskPriority.normal
    due_at: UtcDatetime | None = None
    project_id: UUID | None = None
    module_id: UUID | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 140:
            raise ValueError("Le titre doit contenir entre 2 et 140 caractères.")
        return cleaned

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 1000)


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_at: UtcDatetime | None = None
    project_id: UUID | None = None
    module_id: UUID | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Le titre ne peut pas être null.")
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 140:
            raise ValueError("Le titre doit contenir entre 2 et 140 caractères.")
        return cleaned

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 1000)

    @field_validator("status", "priority")
    @classmethod
    def reject_explicit_null(cls, value: TaskStatus | TaskPriority | None) -> TaskStatus | TaskPriority:
        if value is None:
            raise ValueError("Ce champ ne peut pas être null.")
        return value


class TaskResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    description: str | None = None
    status: TaskStatus
    priority: TaskPriority
    due_at: datetime | None = None
    completed_at: datetime | None = None
    source: TaskSource
    proposal_id: UUID | None = None
    project_id: UUID | None = None
    module_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class TaskSummary(BaseModel):
    active_count: int
    done_count: int
    parked_count: int
    cancelled_count: int
    overdue_count: int
    completion_rate: int
