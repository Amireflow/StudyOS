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
    LearningStatus,
    ObjectiveCategory,
    ObjectiveStatus,
    ProjectStatus,
    ProposalStatus,
    ScheduleEventType,
    SkillAssessmentType,
    SkillEvidenceType,
    StrategicDecision,
    TaskPriority,
    TaskStatus,
    UtcDatetime,
    normalize_optional_text,
    validate_optional_http_url,
)


class AiToolSpec(BaseModel):
    name: str
    access: Literal["read", "proposal"]
    risk_level: Literal["read", "simple", "structuring", "sensitive"] = "structuring"
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
    idempotency_key: str | None = Field(default=None, max_length=80)
    auto_execute_simple: bool | None = None

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 2000:
            raise ValueError("Le message doit contenir entre 2 et 2000 caractères.")
        return cleaned

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 80)


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
    auto_executed_count: int = 0


class AcceptProposalRequest(BaseModel):
    payload_overrides: dict[str, Any] | None = None
    idempotency_key: str | None = Field(default=None, max_length=80)

    @field_validator("idempotency_key")
    @classmethod
    def validate_idempotency_key(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 80)


class AiMemoryResponse(BaseModel):
    user_id: UUID
    academic_context: dict[str, Any] = Field(default_factory=dict)
    availability_preferences: dict[str, Any] = Field(default_factory=dict)
    learning_preferences: dict[str, Any] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    long_term_goals: list[str] = Field(default_factory=list)
    recent_decisions: list[dict[str, Any]] = Field(default_factory=list)
    execution_history: list[dict[str, Any]] = Field(default_factory=list)
    weekly_study_hours: int | None = None
    default_session_minutes: int = 60
    auto_execute_simple_actions: bool = False
    updated_at: datetime


class AiMemoryUpdateRequest(BaseModel):
    academic_context: dict[str, Any] | None = None
    availability_preferences: dict[str, Any] | None = None
    learning_preferences: dict[str, Any] | None = None
    constraints: list[str] | None = None
    long_term_goals: list[str] | None = None
    weekly_study_hours: int | None = Field(default=None, ge=0, le=120)
    default_session_minutes: int | None = Field(default=None, ge=15, le=240)
    auto_execute_simple_actions: bool | None = None


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


class PauseProjectProposalPayload(BaseModel):
    project_id: UUID
    reason: str | None = None

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 300)


class EnsureAiReportsResponse(BaseModel):
    daily_briefing: AiReportResponse
    weekly_review: AiReportResponse
    created_daily: bool = False
    created_weekly: bool = False


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
    create_course: bool = False
    course_subject: str | None = None
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


class UpdateTaskProposalPayload(BaseModel):
    task_id: UUID
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
            return None
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 140:
            raise ValueError("Le titre de la tâche doit contenir entre 2 et 140 caractères.")
        return cleaned

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 1000)


class CreateProjectProposalPayload(BaseModel):
    name: str
    category: str = "project"
    description: str | None = None
    goal: str
    status: ProjectStatus = ProjectStatus.active
    priority: TaskPriority = TaskPriority.normal
    motivation: str | None = None
    weekly_target_minutes: int = Field(default=180, ge=0, le=3000)
    next_action: str = "Définir la première étape concrète"
    deliverables: list[str] = Field(default_factory=list)
    goal_id: UUID | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 140:
            raise ValueError("Le nom du projet doit contenir entre 2 et 140 caractères.")
        return cleaned

    @field_validator("description", "motivation")
    @classmethod
    def validate_optional_long(cls, value: str | None) -> str | None:
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
        cleaned = (value or "").strip()
        if len(cleaned) > 240:
            raise ValueError("La prochaine action ne doit pas dépasser 240 caractères.")
        return cleaned


class UpdateProjectProposalPayload(BaseModel):
    project_id: UUID
    name: str | None = None
    description: str | None = None
    goal: str | None = None
    status: ProjectStatus | None = None
    priority: TaskPriority | None = None
    next_action: str | None = None
    weekly_target_minutes: int | None = Field(default=None, ge=0, le=3000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
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
    def validate_goal(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 300:
            raise ValueError("L’objectif du projet doit contenir entre 2 et 300 caractères.")
        return cleaned

    @field_validator("next_action")
    @classmethod
    def validate_next_action(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 240)


class CreateSkillProposalPayload(BaseModel):
    name: str
    domain: str = "Développement"
    description: str | None = None
    target_level: int | None = Field(default=3, ge=1, le=5)
    goal_id: UUID | None = None
    learning_path_id: UUID | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 120:
            raise ValueError("Le nom de la compétence doit contenir entre 2 et 120 caractères.")
        return cleaned

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str) -> str:
        cleaned = (value or "").strip() or "Général"
        if len(cleaned) < 2 or len(cleaned) > 80:
            raise ValueError("Le domaine doit contenir entre 2 et 80 caractères.")
        return cleaned

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 1000)


class CreateLearningPathProposalPayload(BaseModel):
    title: str
    goal: str
    description: str | None = None
    status: LearningStatus = LearningStatus.active
    modules: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 140:
            raise ValueError("Le titre du parcours doit contenir entre 2 et 140 caractères.")
        return cleaned

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 300:
            raise ValueError("L’objectif du parcours doit contenir entre 2 et 300 caractères.")
        return cleaned

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 1000)


class UpdateLearningPathProposalPayload(BaseModel):
    path_id: UUID
    title: str | None = None
    goal: str | None = None
    description: str | None = None
    status: LearningStatus | None = None
    add_module_title: str | None = None
    add_lesson_title: str | None = None

    @field_validator("title", "add_module_title", "add_lesson_title")
    @classmethod
    def validate_short_titles(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 140)

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 300)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 1000)


class CreatePersonalGoalProposalPayload(BaseModel):
    title: str
    category: ObjectiveCategory = ObjectiveCategory.learning_goal
    goal: str
    description: str | None = None
    current_level: int | None = Field(default=0, ge=0, le=5)
    target_level: int | None = Field(default=3, ge=1, le=5)
    priority: TaskPriority = TaskPriority.high
    is_primary: bool = False
    motivation: str | None = None
    weekly_target_minutes: int = Field(default=180, ge=0, le=2400)
    next_action: str = "Planifier la première séance"
    create_linked_entities: bool = True

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 140:
            raise ValueError("Le titre de l’objectif doit contenir entre 2 et 140 caractères.")
        return cleaned

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 300:
            raise ValueError("La description d’objectif doit contenir entre 2 et 300 caractères.")
        return cleaned

    @field_validator("description", "motivation")
    @classmethod
    def validate_long(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 2000)

    @field_validator("next_action")
    @classmethod
    def validate_next_action(cls, value: str) -> str:
        cleaned = (value or "").strip()
        if len(cleaned) > 240:
            raise ValueError("La prochaine action ne doit pas dépasser 240 caractères.")
        return cleaned


class UpdatePersonalGoalProposalPayload(BaseModel):
    goal_id: UUID
    title: str | None = None
    goal: str | None = None
    description: str | None = None
    priority: TaskPriority | None = None
    status: ObjectiveStatus | None = None
    is_primary: bool | None = None
    weekly_target_minutes: int | None = Field(default=None, ge=0, le=2400)
    next_action: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 140)

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 300)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 2000)

    @field_validator("next_action")
    @classmethod
    def validate_next_action(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 240)


class CreateStudySessionProposalPayload(BaseModel):
    title: str
    category: str = "Apprentissage"
    planned_activity: str | None = None
    started_at: UtcDatetime | None = None
    project_id: UUID | None = None
    goal_id: UUID | None = None
    task_id: UUID | None = None
    skill_id: UUID | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 140:
            raise ValueError("Le titre de la séance doit contenir entre 2 et 140 caractères.")
        return cleaned

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        cleaned = (value or "").strip() or "Apprentissage"
        if len(cleaned) > 60:
            raise ValueError("La catégorie ne doit pas dépasser 60 caractères.")
        return cleaned

    @field_validator("planned_activity")
    @classmethod
    def validate_planned_activity(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 240)


class UpdateScheduleEventProposalPayload(BaseModel):
    event_id: UUID
    title: str | None = None
    starts_at: UtcDatetime | None = None
    ends_at: UtcDatetime | None = None
    notes: str | None = None
    reason: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 140)

    @field_validator("notes", "reason")
    @classmethod
    def validate_notes(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 500)

    @model_validator(mode="after")
    def validate_dates(self) -> "UpdateScheduleEventProposalPayload":
        if self.starts_at is not None and self.ends_at is not None and self.ends_at <= self.starts_at:
            raise ValueError("L’heure de fin doit être strictement postérieure au début.")
        return self


class ArchiveScheduleEventProposalPayload(BaseModel):
    event_id: UUID
    reason: str | None = None

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 300)


class UpdatePreferencesProposalPayload(BaseModel):
    weekly_study_hours: int | None = Field(default=None, ge=0, le=120)
    study_start_hour: int | None = Field(default=None, ge=5, le=20)
    study_end_hour: int | None = Field(default=None, ge=6, le=23)
    max_daily_study_minutes: int | None = Field(default=None, ge=60, le=480)
    preferred_session_minutes: int | None = Field(default=None, ge=30, le=180)
    excluded_days: list[Any] | None = None
    ai_instructions: str | None = None
    constraints: list[str] | None = None
    long_term_goals: list[str] | None = None
    academic_context: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_hours(self) -> "UpdatePreferencesProposalPayload":
        if (
            self.study_start_hour is not None
            and self.study_end_hour is not None
            and self.study_end_hour <= self.study_start_hour
        ):
            raise ValueError("L’heure de fin doit être supérieure à l’heure de début.")
        return self


class ManageAvailabilityRuleProposalPayload(BaseModel):
    label: str = Field(..., min_length=2, max_length=120)
    rule_type: Literal["personal_unavailability", "confirmed_availability", "recovery_time"] = (
        "personal_unavailability"
    )
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    start_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    end_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    starts_at: UtcDatetime | None = None
    ends_at: UtcDatetime | None = None
    timezone: str = Field(default="Europe/Paris", min_length=2, max_length=64)
    recurrence: Literal["once", "weekly", "daily"] = "weekly"
    notes: str | None = Field(default=None, max_length=500)


class GenerateLearningPlanProposalPayload(BaseModel):
    horizon_days: int = Field(default=7, ge=1, le=30)
    focus_subject: str | None = Field(default=None, max_length=120)
    exam_title: str | None = Field(default=None, max_length=160)
    exam_at: UtcDatetime | None = None
    weekly_hours_override: float | None = Field(default=None, gt=0.5, le=80)
    daily_max_minutes: int | None = Field(default=None, ge=30, le=600)
    preferred_session_minutes: int | None = Field(default=None, ge=25, le=180)
    include_potential_slots: bool = True
    create_missing_courses: bool = False
    apply_immediately: bool = True
    replace_future_planned: bool = True
    plan_version_id: UUID | None = None
    instruction: str | None = Field(default=None, max_length=500)


class BatchActionStep(BaseModel):
    action_type: AiActionType
    payload: dict[str, Any] = Field(default_factory=dict)
    link_to_step: dict[str, int] | None = None

    @field_validator("action_type")
    @classmethod
    def forbid_nested_batch(cls, value: AiActionType) -> AiActionType:
        if value == AiActionType.batch_actions:
            raise ValueError("L’imbrication de batch_actions n’est pas autorisée.")
        return value


class BatchActionsProposalPayload(BaseModel):
    summary: str | None = None
    steps: list[BatchActionStep] = Field(min_length=1, max_length=12)
    compensate_on_failure: bool = True

    @field_validator("summary")
    @classmethod
    def validate_summary(cls, value: str | None) -> str | None:
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
    "AiMemoryResponse",
    "AiMemoryUpdateRequest",
    "CreateTaskProposalPayload",
    "UpdateTaskProposalPayload",
    "ParkTaskProposalPayload",
    "CreateProjectProposalPayload",
    "UpdateProjectProposalPayload",
    "PauseProjectProposalPayload",
    "EnsureAiReportsResponse",
    "CreateScheduleProposalPayload",
    "UpdateScheduleEventProposalPayload",
    "ArchiveScheduleEventProposalPayload",
    "CreateStudySessionProposalPayload",
    "CreateSkillProposalPayload",
    "AddEvidenceProposalPayload",
    "ProposeSkillAssessmentPayload",
    "RecommendSkillProgressionPayload",
    "CreateLearningPathProposalPayload",
    "UpdateLearningPathProposalPayload",
    "CreatePersonalGoalProposalPayload",
    "UpdatePersonalGoalProposalPayload",
    "ProposedActivitySlot",
    "PlanStrategicActivityProposalPayload",
    "CreateCourseProposalPayload",
    "UpdatePreferencesProposalPayload",
    "BatchActionStep",
    "BatchActionsProposalPayload",
    "RawProposalCandidate",
    "AiProviderKind",
    "AiProviderCatalogItem",
    "AiProviderModelInfo",
    "AiProviderConfigResponse",
    "AiProviderConfigUpdate",
    "FetchProviderModelsRequest",
    "FetchProviderModelsResponse",
]
