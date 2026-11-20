from datetime import datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from app.schemas.common import (
    ObjectiveCategory,
    ObjectiveStatus,
    TaskPriority,
    UtcDatetime,
    normalize_optional_text,
)


class PersonalGoalCreate(BaseModel):
    title: str
    category: ObjectiveCategory = ObjectiveCategory.learning_goal
    description: str | None = None
    goal: str | None = None
    current_level: int | None = Field(default=None, ge=0, le=5)
    target_level: int | None = Field(default=None, ge=1, le=5)
    priority: TaskPriority = TaskPriority.normal
    is_primary: bool = False
    motivation: str | None = None
    start_date: UtcDatetime | None = None
    target_date: UtcDatetime | None = None
    weekly_target_minutes: int = Field(default=120, ge=0, le=2400)
    status: ObjectiveStatus = ObjectiveStatus.active
    steps: list[dict[str, Any]] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    next_action: str = ""
    success_criteria: list[str] = Field(default_factory=list)
    create_linked_entities: bool = True

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 140:
            raise ValueError("Le titre de l’objectif doit contenir entre 2 et 140 caractères.")
        return cleaned

    @field_validator("description", "motivation")
    @classmethod
    def validate_optional_long(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 2000)

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, value: str | None) -> str | None:
        return normalize_optional_text(value, 300)

    @field_validator("next_action")
    @classmethod
    def validate_next_action(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) > 240:
            raise ValueError("La prochaine action ne doit pas dépasser 240 caractères.")
        return cleaned


class PersonalGoalUpdate(BaseModel):
    title: str | None = None
    category: ObjectiveCategory | None = None
    description: str | None = None
    goal: str | None = None
    current_level: int | None = Field(default=None, ge=0, le=5)
    target_level: int | None = Field(default=None, ge=1, le=5)
    priority: TaskPriority | None = None
    is_primary: bool | None = None
    motivation: str | None = None
    start_date: UtcDatetime | None = None
    target_date: UtcDatetime | None = None
    weekly_target_minutes: int | None = Field(default=None, ge=0, le=2400)
    status: ObjectiveStatus | None = None
    steps: list[dict[str, Any]] | None = None
    deliverables: list[str] | None = None
    next_action: str | None = None
    success_criteria: list[str] | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Le titre ne peut pas être null.")
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 140:
            raise ValueError("Le titre de l’objectif doit contenir entre 2 et 140 caractères.")
        return cleaned


class PersonalGoalResponse(BaseModel):
    id: UUID
    user_id: UUID
    category: ObjectiveCategory
    title: str
    description: str | None = None
    goal: str
    current_level: int | None = None
    target_level: int | None = None
    priority: TaskPriority
    is_primary: bool = False
    motivation: str | None = None
    start_date: datetime | None = None
    target_date: datetime | None = None
    weekly_target_minutes: int
    status: ObjectiveStatus
    steps: list[dict[str, Any]] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    next_action: str = ""
    success_criteria: list[str] = Field(default_factory=list)
    progress_history: list[dict[str, Any]] = Field(default_factory=list)
    skill_id: UUID | None = None
    learning_path_id: UUID | None = None
    course_id: UUID | None = None
    completed_minutes_last_7d: int = 0
    sessions_count: int = 0
    is_behind_schedule: bool = False
    delay_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class ExtractedObjectiveCandidate(BaseModel):
    kind: Literal["personal_goal", "project"]
    category: str
    title: str
    goal: str
    current_level: int | None = None
    target_level: int | None = None
    priority: TaskPriority = TaskPriority.normal
    is_primary: bool = False
    motivation: str | None = None
    weekly_target_minutes: int | None = None
    target_date: str | None = None
    deliverables: list[str] = Field(default_factory=list)
    validation_conditions: list[str] = Field(default_factory=list)
    next_action: str = ""


class ConversationalIntakeRequest(BaseModel):
    message: str
    history: list[dict[str, str]] = Field(default_factory=list)
    known_answers: dict[str, Any] = Field(default_factory=dict)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2 or len(cleaned) > 2000:
            raise ValueError("Le message doit contenir entre 2 et 2000 caractères.")
        return cleaned


class ConversationalIntakeResponse(BaseModel):
    objectives: list[ExtractedObjectiveCandidate]
    current_level: int | str | None = None
    target_level: int | str | None = None
    priority: str | None = None
    motivation: str | None = None
    available_time_weekly_minutes: int | None = None
    target_date: str | None = None
    expected_deliverables: list[str] = Field(default_factory=list)
    validation_conditions: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    progressive_questions: list[str] = Field(default_factory=list)
    requires_confirmation: bool = True
    summary_markdown: str


class ConfirmIntakeRequest(BaseModel):
    objectives: list[ExtractedObjectiveCandidate]
    available_time_weekly_minutes: int | None = Field(default=None, ge=30, le=3000)
    motivation: str | None = None
    target_date: UtcDatetime | None = None
    primary_title: str | None = None


class ConfirmIntakeResponse(BaseModel):
    created_goals: list[PersonalGoalResponse]
    created_projects: list[dict[str, Any]]
    active_priority_title: str | None = None


class UnifiedPlanSlot(BaseModel):
    source_category: Literal[
        "academic_obligation",
        "personal_goal",
        "project",
        "revision",
        "evaluation",
        "recovery",
    ]
    is_fixed: bool
    title: str
    day_label: str
    local_date: str
    local_start_time: str
    local_end_time: str
    starts_at: str
    ends_at: str
    duration_minutes: int
    expected_outcome: str
    linked_goal_id: str | None = None
    linked_project_id: str | None = None
    linked_skill_id: str | None = None
    linked_path_id: str | None = None
    linked_module_id: str | None = None
    linked_lesson_id: str | None = None
    linked_task_id: str | None = None


class UnifiedPlanGenerateRequest(BaseModel):
    weekly_available_minutes: int | None = Field(default=None, ge=60, le=3000)
    primary_priority_title: str | None = None
    target_week_start: str | None = None
    include_daily_recovery: bool = True


class UnifiedPlanAdaptationItem(BaseModel):
    target_title: str
    target_kind: Literal["personal_goal", "project", "academic"]
    cause: str
    action_taken: str


class UnifiedPlanResponse(BaseModel):
    week_start: str
    primary_priority_title: str | None = None
    secondary_objectives: list[str] = Field(default_factory=list)
    academic_fixed_slots: list[UnifiedPlanSlot] = Field(default_factory=list)
    flexible_study_slots: list[UnifiedPlanSlot] = Field(default_factory=list)
    recovery_slots: list[UnifiedPlanSlot] = Field(default_factory=list)
    daily_breakdown: dict[str, list[UnifiedPlanSlot]] = Field(default_factory=dict)
    arbitrages: list[str] = Field(default_factory=list)
    adaptations: list[UnifiedPlanAdaptationItem] = Field(default_factory=list)
    displaced_conflicts_count: int = 0
    total_academic_minutes: int = 0
    total_personal_goal_minutes: int = 0
    total_project_minutes: int = 0
    requires_validation: bool = True


class UnifiedPlanApplyRequest(BaseModel):
    flexible_study_slots: list[UnifiedPlanSlot]
    primary_priority_title: str | None = None
    replace_existing_flexible_week: bool = True
    week_start: str | None = None


class UnifiedPlanApplyResponse(BaseModel):
    created_events_count: int
    displaced_conflicts_count: int
    linked_tasks_created_count: int
    active_priority_title: str | None = None


class ObjectivesOverviewResponse(BaseModel):
    academic_obligations: list[dict[str, Any]]
    personal_goals: list[PersonalGoalResponse]
    projects: list[dict[str, Any]]
    priority_summary: dict[str, Any]
