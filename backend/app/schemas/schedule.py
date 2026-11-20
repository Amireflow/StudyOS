from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator
from app.schemas.common import (
    CourseSessionSubtype,
    ScheduleEventSource,
    ScheduleEventType,
    TimetableAnomalyType,
    TimetableFileFormat,
    TimetableImportStatus,
    UtcDatetime,
    normalize_optional_text,
)


class ScheduleEventCreate(BaseModel):
    title: str
    type: ScheduleEventType = ScheduleEventType.course
    starts_at: UtcDatetime
    ends_at: UtcDatetime
    notes: str | None = None
    source: ScheduleEventSource = ScheduleEventSource.manual
    import_id: UUID | None = None
    session_subtype: CourseSessionSubtype | None = None
    teacher: str | None = None
    room: str | None = None
    group_name: str | None = None

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

    @field_validator("teacher")
    @classmethod
    def validate_teacher(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 120)

    @field_validator("room", "group_name")
    @classmethod
    def validate_short_meta(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 100)

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
    session_subtype: CourseSessionSubtype | None = None
    teacher: str | None = None
    room: str | None = None
    group_name: str | None = None

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

    @field_validator("teacher")
    @classmethod
    def validate_teacher(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 120)

    @field_validator("room", "group_name")
    @classmethod
    def validate_short_meta(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 100)

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
    source: ScheduleEventSource = ScheduleEventSource.manual
    import_id: UUID | None = None
    session_subtype: str | None = None
    teacher: str | None = None
    room: str | None = None
    group_name: str | None = None
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


class ExtractedCourseRowSchema(BaseModel):
    row_id: str
    subject: str = ""
    day_of_week: int | None = None
    day_label: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    teacher: str | None = None
    room: str | None = None
    group_name: str | None = None
    session_type: CourseSessionSubtype = CourseSessionSubtype.cours
    valid_from: str | None = None
    valid_until: str | None = None
    uncertain: bool = False
    uncertainty_reasons: list[str] = Field(default_factory=list)
    ignored: bool = False
    raw_excerpt: str | None = None

    @field_validator("subject")
    @classmethod
    def normalize_subject(cls, value: str) -> str:
        return value.strip()[:140]

    @field_validator("teacher")
    @classmethod
    def normalize_teacher(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 120)

    @field_validator("room", "group_name")
    @classmethod
    def normalize_short_field(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 100)


class TimetableAnomalySchema(BaseModel):
    id: str
    row_id: str | None = None
    related_row_id: str | None = None
    type: TimetableAnomalyType
    severity: str = "error"
    message: str


class TimetableImportAnalyzeBase64Request(BaseModel):
    filename: str
    content_type: str = "application/octet-stream"
    content_base64: str


class TimetableImportUpdateDraftRequest(BaseModel):
    courses: list[ExtractedCourseRowSchema]
    valid_from: str | None = None
    valid_until: str | None = None


class TimetableImportConfirmRequest(BaseModel):
    courses: list[ExtractedCourseRowSchema] | None = None
    valid_from: str | None = None
    valid_until: str | None = None
    target_week_start: date | None = None
    recurrence_weeks: int = Field(default=1, ge=1, le=24)
    replace_existing_imported: bool = False


class TimetableImportResponse(BaseModel):
    id: UUID
    user_id: UUID
    filename: str
    file_format: TimetableFileFormat
    mime_type: str
    file_size_bytes: int
    source_preview_text: str | None = None
    source_deleted: bool = False
    status: TimetableImportStatus
    valid_from: str | None = None
    valid_until: str | None = None
    extracted_courses: list[ExtractedCourseRowSchema] = Field(default_factory=list)
    anomalies: list[TimetableAnomalySchema] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocking_anomalies_count: int = 0
    created_events_count: int = 0
    skipped_duplicates_count: int = 0
    replaced_events_count: int = 0
    created_at: datetime
    updated_at: datetime
    validated_at: datetime | None = None


class TimetableImportConfirmResponse(BaseModel):
    import_record: TimetableImportResponse
    created_events: list[ScheduleEventResponse]
    created_count: int
    skipped_duplicates_count: int
    replaced_count: int
