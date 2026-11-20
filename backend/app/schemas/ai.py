from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator
from app.schemas.common import (
    AiActionType,
    AiContextScope,
    AiMessageRole,
    AiReportType,
    ProposalStatus,
    ScheduleEventType,
    SkillEvidenceType,
    TaskPriority,
    UtcDatetime,
    normalize_optional_text,
    validate_optional_http_url,
)


class AiToolSpec(BaseModel):
    name: str
    access: Literal["read", "proposal"]
    label: str
    description: str
    requires_confirmation: bool
    parameter_keys: list[str]


class AiConversationCreate(BaseModel):
    title: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 160)


class AiConversationResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class AiMessageCreate(BaseModel):
    content: str
    context_scopes: list[AiContextScope] | None = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 2000:
            raise ValueError("Le message doit contenir entre 2 et 2000 caractères.")
        return cleaned


class AiMessageResponse(BaseModel):
    id: UUID
    user_id: UUID
    conversation_id: UUID
    role: AiMessageRole
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class AiActionProposalResponse(BaseModel):
    id: UUID
    user_id: UUID
    conversation_id: UUID
    action_type: str
    title: str
    explanation: str
    payload: dict[str, Any]
    status: ProposalStatus
    expires_at: datetime | None = None
    execution_result: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None


class AiConversationDetailResponse(BaseModel):
    conversation: AiConversationResponse
    messages: list[AiMessageResponse]
    proposals: list[AiActionProposalResponse]


class AiTurnResponse(BaseModel):
    user_message: AiMessageResponse
    assistant_message: AiMessageResponse
    proposals: list[AiActionProposalResponse]


class AcceptProposalRequest(BaseModel):
    payload_overrides: dict[str, Any] | None = None


class RejectProposalRequest(BaseModel):
    reason: str | None = None

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 500)


class AiReportResponse(BaseModel):
    id: UUID
    user_id: UUID
    type: AiReportType
    period_start: datetime
    period_end: datetime
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


# Schémas stricts de validation des paramètres d'actions proposées (AI-01, ActionValidator)


class CreateTaskProposalPayload(BaseModel):
    title: str
    description: str | None = None
    priority: TaskPriority = TaskPriority.normal
    due_at: UtcDatetime | None = None
    project_id: UUID | None = None
    module_id: UUID | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 140:
            raise ValueError("Le titre de la tâche proposée doit contenir entre 2 et 140 caractères.")
        return cleaned

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 1000)


class ParkTaskProposalPayload(BaseModel):
    task_id: UUID
    reason: str | None = None

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 300)


class CreateScheduleProposalPayload(BaseModel):
    title: str
    type: ScheduleEventType = ScheduleEventType.learning
    starts_at: UtcDatetime
    ends_at: UtcDatetime
    notes: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 140:
            raise ValueError("Le titre du créneau doit contenir entre 2 et 140 caractères.")
        return cleaned

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 500)

    @model_validator(mode="after")
    def validate_range(self) -> "CreateScheduleProposalPayload":
        if self.ends_at <= self.starts_at:
            raise ValueError("L’heure de fin du créneau proposé doit être postérieure au début.")
        return self


class AddEvidenceProposalPayload(BaseModel):
    skill_id: UUID
    type: SkillEvidenceType = SkillEvidenceType.exercise
    description: str
    reference_url: str | None = None
    result: str | None = None

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


class UpdateSkillLevelProposalPayload(BaseModel):
    skill_id: UUID
    current_level: int
    target_level: int | None = None

    @field_validator("current_level")
    @classmethod
    def validate_current_level(cls, value: int) -> int:
        if value < 0 or value > 5:
            raise ValueError("Le niveau de compétence proposé doit être compris entre 0 et 5.")
        return value

    @field_validator("target_level")
    @classmethod
    def validate_target_level(cls, value: int | None) -> int | None:
        if value is not None and (value < 0 or value > 5):
            raise ValueError("Le niveau cible doit être compris entre 0 et 5.")
        return value


class RawProposalCandidate(BaseModel):
    action_type: str
    title: str
    explanation: str
    payload: dict[str, Any]


__all__ = [
    "AiActionType",
    "AiToolSpec",
    "AiConversationCreate",
    "AiConversationResponse",
    "AiConversationDetailResponse",
    "AiMessageCreate",
    "AiMessageResponse",
    "AiTurnResponse",
    "AiActionProposalResponse",
    "AcceptProposalRequest",
    "RejectProposalRequest",
    "AiReportResponse",
    "CreateTaskProposalPayload",
    "ParkTaskProposalPayload",
    "CreateScheduleProposalPayload",
    "AddEvidenceProposalPayload",
    "UpdateSkillLevelProposalPayload",
    "RawProposalCandidate",
]
