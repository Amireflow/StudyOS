from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator
from app.schemas.common import ScheduleEventType, UtcDatetime, normalize_optional_text


class ScheduleEventCreate(BaseModel):
    title: str
    type: ScheduleEventType = ScheduleEventType.course
    starts_at: UtcDatetime
    ends_at: UtcDatetime
    notes: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 140:
            raise ValueError("Le titre doit contenir entre 2 et 140 caractères.")
        return cleaned

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 1000)

    @model_validator(mode="after")
    def validate_time_range(self) -> "ScheduleEventCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("L’heure de fin doit être strictement postérieure au début.")
        return self


class ScheduleEventUpdate(BaseModel):
    title: str | None = None
    type: ScheduleEventType | None = None
    starts_at: UtcDatetime | None = None
    ends_at: UtcDatetime | None = None
    notes: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Le titre ne peut pas être null.")
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 140:
            raise ValueError("Le titre doit contenir entre 2 et 140 caractères.")
        return cleaned

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 1000)

    @field_validator("type", "starts_at", "ends_at")
    @classmethod
    def reject_explicit_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("Ce champ ne peut pas être null.")
        return value

    @model_validator(mode="after")
    def validate_partial_range(self) -> "ScheduleEventUpdate":
        if self.starts_at is not None and self.ends_at is not None:
            if self.ends_at <= self.starts_at:
                raise ValueError("L’heure de fin doit être strictement postérieure au début.")
        return self


class ScheduleEventResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    type: ScheduleEventType
    starts_at: datetime
    ends_at: datetime
    notes: str | None = None
    duration_minutes: int
    has_conflict: bool = False
    conflicting_event_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class DuplicateWeekRequest(BaseModel):
    source_week_start: date


class DuplicateWeekResponse(BaseModel):
    created: list[ScheduleEventResponse]
    created_count: int
    skipped_count: int
