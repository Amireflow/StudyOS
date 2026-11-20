from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, model_validator
from app.schemas.common import (
    AiActionType,
    AiContextScope,
    AiMessageRole,
    AiReportType,
    CourseLanguage,
    ProposalStatus,
    ScheduleEventType,
    SkillAssessmentType,
    SkillEvidenceType,
    StrategicDecision,
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


class UpdateProposalRequest(BaseModel):
    payload_overrides: dict[str, Any] = Field(default_factory=dict)
    recalculate_slots: bool = False


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


class ProposeSkillAssessmentPayload(BaseModel):
    skill_id: UUID
    target_level: int | None = None
    assessment_type: SkillAssessmentType = SkillAssessmentType.practical_exercise
    prompt_title: str | None = None
    prompt_instructions: str | None = None
    path_id: UUID | None = None
    module_id: UUID | None = None
    lesson_id: UUID | None = None

    @field_validator("target_level")
    @classmethod
    def validate_target_level(cls, value: int | None) -> int | None:
        if value is not None and (value < 1 or value > 5):
            raise ValueError("Le niveau visé doit être compris entre 1 et 5.")
        return value

    @field_validator("prompt_title")
    @classmethod
    def validate_prompt_title(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 180)

    @field_validator("prompt_instructions")
    @classmethod
    def validate_prompt_instructions(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 4000)


class RecommendSkillProgressionPayload(BaseModel):
    skill_id: UUID
    assessment_id: UUID
    proposed_level: int
    evidence_ids: list[UUID] = Field(default_factory=list)
    decision_reason: str | None = None

    @field_validator("proposed_level")
    @classmethod
    def validate_proposed_level(cls, value: int) -> int:
        if value < 1 or value > 5:
            raise ValueError("Le niveau recommandé doit être compris entre 1 et 5.")
        return value

    @field_validator("decision_reason")
    @classmethod
    def validate_decision_reason(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 500)


class ProposedActivitySlot(BaseModel):
    day_label: str
    local_date: str
    local_start_time: str
    local_end_time: str
    starts_at: UtcDatetime
    ends_at: UtcDatetime
    duration_minutes: int = Field(ge=15, le=240)

    @field_validator("local_date")
    @classmethod
    def validate_local_date(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) != 10 or cleaned[4] != "-" or cleaned[7] != "-":
            raise ValueError("La date locale du créneau doit être au format YYYY-MM-DD.")
        return cleaned

    @model_validator(mode="after")
    def validate_range(self) -> "ProposedActivitySlot":
        if self.ends_at <= self.starts_at:
            raise ValueError("L’heure de fin du créneau proposé doit être strictement postérieure au début.")
        return self


class PlanStrategicActivityProposalPayload(BaseModel):
    activity_title: str
    category: Literal[
        "learning",
        "project",
        "exam_prep",
        "personal",
        "university_deepening",
    ] = "learning"
    goal: str
    decision: StrategicDecision = StrategicDecision.acceptable
    conditions: list[str] = Field(default_factory=list)
    opportunity_cost_note: str | None = None
    create_learning_path: bool = True
    create_project: bool = False
    park_only: bool = False
    frequency_per_week: int = Field(default=2, ge=0, le=7)
    session_duration_minutes: int = Field(default=60, ge=30, le=240)
    estimated_weeks: int = Field(default=3, ge=1, le=52)
    start_date: str | None = None
    proposed_slots: list[ProposedActivitySlot] = Field(default_factory=list)

    @field_validator("activity_title")
    @classmethod
    def validate_activity_title(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 140:
            raise ValueError("Le titre de l’activité doit contenir entre 2 et 140 caractères.")
        return cleaned

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 300:
            raise ValueError("L’objectif mesurable doit contenir entre 2 et 300 caractères.")
        return cleaned

    @field_validator("opportunity_cost_note")
    @classmethod
    def validate_opportunity_cost_note(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 500)

    @model_validator(mode="after")
    def validate_slots_requirement(self) -> "PlanStrategicActivityProposalPayload":
        if not self.park_only and len(self.proposed_slots) < 1:
            raise ValueError(
                "Au moins un créneau réel disponible est requis pour programmer une activité."
            )
        return self


class CreateCourseProposalPayload(BaseModel):
    subject: str
    title: str | None = None
    domain: str | None = None
    language: CourseLanguage = CourseLanguage.fr
    total_levels: int = Field(default=3, ge=2, le=5)
    goal: str | None = None

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 120:
            raise ValueError("Le sujet du cours proposé doit contenir entre 2 et 120 caractères.")
        return cleaned

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 160)

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 80)

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 300)


class RawProposalCandidate(BaseModel):
    action_type: str
    title: str
    explanation: str
    payload: dict[str, Any]


AiProviderKind = Literal["local", "river", "openai_compatible", "gemini"]


def _canonicalize_provider_kind(value: Any) -> str:
    cleaned = str(value or "local").strip().lower()
    if cleaned in ("river", "river_ai", "river-ai", "riverai", "console.river.ai", "api.river.ai"):
        return "river"
    if cleaned in ("openai", "openai_compatible", "openai-compatible"):
        return "openai_compatible"
    if cleaned in ("gemini", "google"):
        return "gemini"
    return cleaned


class AiProviderCatalogItem(BaseModel):
    id: AiProviderKind
    label: str
    console_url: str | None = None
    default_base_url: str
    requires_api_key: bool


class AiProviderModelInfo(BaseModel):
    id: str
    label: str
    owned_by: str | None = None
    context_window: int | None = None


class AiProviderConfigResponse(BaseModel):
    provider: AiProviderKind
    base_url: str
    model: str
    has_api_key: bool
    api_key_preview: str | None = None
    source: Literal["user", "server_env", "default"]
    available_providers: list[AiProviderCatalogItem] = Field(default_factory=list)


class AiProviderConfigUpdate(BaseModel):
    provider: AiProviderKind
    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None
    clear_api_key: bool = False

    @field_validator("provider", mode="before")
    @classmethod
    def normalize_provider(cls, value: Any) -> str:
        return _canonicalize_provider_kind(value)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 300)

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 160)

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 500)


class FetchProviderModelsRequest(BaseModel):
    provider: AiProviderKind = "river"
    api_key: str | None = None
    base_url: str | None = None

    @field_validator("provider", mode="before")
    @classmethod
    def normalize_provider(cls, value: Any) -> str:
        if value is None or (isinstance(value, str) and not value.strip()):
            return "river"
        return _canonicalize_provider_kind(value)

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 500)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 300)


class FetchProviderModelsResponse(BaseModel):
    provider: AiProviderKind
    base_url: str
    models: list[AiProviderModelInfo] = Field(default_factory=list)
    count: int


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
    "UpdateProposalRequest",
    "RejectProposalRequest",
    "AiReportResponse",
    "CreateTaskProposalPayload",
    "ParkTaskProposalPayload",
    "CreateScheduleProposalPayload",
    "AddEvidenceProposalPayload",
    "ProposeSkillAssessmentPayload",
    "RecommendSkillProgressionPayload",
    "ProposedActivitySlot",
    "PlanStrategicActivityProposalPayload",
    "CreateCourseProposalPayload",
    "RawProposalCandidate",
    "AiProviderKind",
    "AiProviderCatalogItem",
    "AiProviderModelInfo",
    "AiProviderConfigResponse",
    "AiProviderConfigUpdate",
    "FetchProviderModelsRequest",
    "FetchProviderModelsResponse",
]
