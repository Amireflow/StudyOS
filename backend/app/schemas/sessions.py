from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, field_validator, model_validator
from app.schemas.common import SessionStatus, UtcDatetime, normalize_optional_text


class SessionCreate(BaseModel):
    title: str
    category: str
    started_at: UtcDatetime | None = None
    ended_at: UtcDatetime | None = None
    result: str | None = None
    planned_activity: str | None = None
    actual_activity: str | None = None
    outcome_status: str | None = None
    deliverable_summary: str | None = None
    blockers: str | None = None
    next_step: str | None = None
    task_id: UUID | None = None
    project_id: UUID | None = None
    goal_id: UUID | None = None
    module_id: UUID | None = None
    lesson_id: UUID | None = None
    skill_id: UUID | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 140:
            raise ValueError("Le titre doit contenir entre 2 et 140 caractères.")
        return cleaned

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned or len(cleaned) > 60:
            raise ValueError("La catégorie doit contenir entre 1 et 60 caractères.")
        return cleaned

    @field_validator("result")
    @classmethod
    def validate_result(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 1000)

    @model_validator(mode="after")
    def validate_completed_payload(self) -> "SessionCreate":
        if self.ended_at is not None:
            if self.started_at is None:
                raise ValueError("L’heure de début est requise lorsqu’une heure de fin est fournie.")
            if self.ended_at <= self.started_at:
                raise ValueError("L’heure de fin doit être strictement postérieure au début.")
            if not self.result or len(self.result) < 2:
                raise ValueError("Notez brièvement ce qui a été produit ou appris (min. 2 caractères).")
        return self


class SessionFinish(BaseModel):
    result: str
    ended_at: UtcDatetime | None = None
    planned_activity: str | None = None
    actual_activity: str | None = None
    outcome_status: str | None = None
    deliverable_summary: str | None = None
    blockers: str | None = None
    next_step: str | None = None

    @field_validator("result")
    @classmethod
    def validate_result(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 1000:
            raise ValueError("Le résultat doit contenir entre 2 et 1000 caractères.")
        return cleaned


class SessionUpdate(BaseModel):
    title: str | None = None
    category: str | None = None
    status: SessionStatus | None = None
    result: str | None = None
    planned_activity: str | None = None
    actual_activity: str | None = None
    outcome_status: str | None = None
    deliverable_summary: str | None = None
    blockers: str | None = None
    next_step: str | None = None
    task_id: UUID | None = None
    project_id: UUID | None = None
    goal_id: UUID | None = None
    module_id: UUID | None = None
    lesson_id: UUID | None = None
    skill_id: UUID | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Le titre ne peut pas être null.")
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 140:
            raise ValueError("Le titre doit contenir entre 2 et 140 caractères.")
        return cleaned

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("La catégorie ne peut pas être null.")
        cleaned = value.strip()
        if not cleaned or len(cleaned) > 60:
            raise ValueError("La catégorie doit contenir entre 1 et 60 caractères.")
        return cleaned

    @field_validator("result")
    @classmethod
    def validate_result(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 1000)

    @field_validator("status")
    @classmethod
    def reject_null_status(cls, value: SessionStatus | None) -> SessionStatus:
        if value is None:
            raise ValueError("Le statut ne peut pas être null.")
        return value


class SessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    category: str
    status: SessionStatus
    started_at: datetime
    ended_at: datetime | None = None
    duration_minutes: int
    result: str | None = None
    planned_activity: str | None = None
    actual_activity: str | None = None
    outcome_status: str | None = None
    deliverable_summary: str | None = None
    blockers: str | None = None
    next_step: str | None = None
    task_id: UUID | None = None
    project_id: UUID | None = None
    goal_id: UUID | None = None
    module_id: UUID | None = None
    lesson_id: UUID | None = None
    skill_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class SessionSummary(BaseModel):
    completed_count: int
    total_completed_minutes: int
    in_progress_count: int
    cancelled_count: int
