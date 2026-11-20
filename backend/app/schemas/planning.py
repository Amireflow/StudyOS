from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field, model_validator


class AvailabilityRuleType(str, Enum):
    personal_unavailability = "personal_unavailability"
    confirmed_availability = "confirmed_availability"
    recovery_time = "recovery_time"


class AvailabilityRecurrence(str, Enum):
    once = "once"
    weekly = "weekly"
    daily = "daily"


class SlotCategory(str, Enum):
    fixed_commitment = "fixed_commitment"
    personal_unavailability = "personal_unavailability"
    confirmed_availability = "confirmed_availability"
    potential_availability = "potential_availability"
    recovery_time = "recovery_time"


class PlanVersionStatus(str, Enum):
    proposed = "proposed"
    applied = "applied"
    rejected = "rejected"
    superseded = "superseded"
    restored = "restored"


class AvailabilityRuleCreate(BaseModel):
    label: str = Field(..., min_length=2, max_length=120)
    rule_type: AvailabilityRuleType = AvailabilityRuleType.personal_unavailability
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    start_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    end_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    timezone: str = Field(default="Europe/Paris", min_length=2, max_length=64)
    recurrence: AvailabilityRecurrence = AvailabilityRecurrence.weekly
    active: bool = True
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_window(self) -> "AvailabilityRuleCreate":
        if self.recurrence == AvailabilityRecurrence.once:
            if self.starts_at is None or self.ends_at is None:
                if self.day_of_week is None or not self.start_time or not self.end_time:
                    raise ValueError(
                        "Une règle ponctuelle exige starts_at/ends_at ou day_of_week/start_time/end_time."
                    )
            elif self.ends_at <= self.starts_at:
                raise ValueError("ends_at doit être postérieur à starts_at.")
        else:
            if not self.start_time or not self.end_time:
                raise ValueError("Une règle récurrente exige start_time et end_time (HH:MM).")
            if self.recurrence == AvailabilityRecurrence.weekly and self.day_of_week is None:
                raise ValueError("Une règle hebdomadaire exige day_of_week (0=lundi .. 6=dimanche).")
        for val in (self.start_time, self.end_time):
            if val is not None:
                hh, mm = (int(part) for part in val.split(":"))
                if hh > 23 or mm > 59:
                    raise ValueError("Format horaire invalide (HH:MM attendu).")
        return self


class AvailabilityRuleUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=2, max_length=120)
    rule_type: AvailabilityRuleType | None = None
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    start_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    end_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    timezone: str | None = Field(default=None, min_length=2, max_length=64)
    recurrence: AvailabilityRecurrence | None = None
    active: bool | None = None
    notes: str | None = Field(default=None, max_length=500)


class AvailabilityRuleResponse(BaseModel):
    id: UUID
    user_id: UUID
    label: str
    rule_type: AvailabilityRuleType
    day_of_week: int | None = None
    start_time: str | None = None
    end_time: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    timezone: str
    recurrence: AvailabilityRecurrence
    active: bool
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class TimeSlotWindow(BaseModel):
    start_utc: datetime
    end_utc: datetime
    local_date: str
    start_local: str
    end_local: str
    duration_minutes: int
    category: SlotCategory
    label: str = ""
    source_id: str | None = None


class AvailabilityComputationResponse(BaseModel):
    timezone: str
    range_start: datetime
    range_end: datetime
    fixed_events: list[TimeSlotWindow] = Field(default_factory=list)
    unavailable_slots: list[TimeSlotWindow] = Field(default_factory=list)
    confirmed_slots: list[TimeSlotWindow] = Field(default_factory=list)
    potential_slots: list[TimeSlotWindow] = Field(default_factory=list)
    recovery_slots: list[TimeSlotWindow] = Field(default_factory=list)
    allocatable_slots: list[TimeSlotWindow] = Field(default_factory=list)
    total_confirmed_minutes: int = 0
    total_potential_minutes: int = 0
    total_allocatable_minutes: int = 0
    missing_availability_info: list[str] = Field(default_factory=list)
    summary: str = ""


class LearningPriorityItem(BaseModel):
    source_type: str
    source_id: str | None = None
    title: str
    subject: str
    domain: str
    score: float
    urgency_score: float = 0.0
    blocking_score: float = 0.0
    strategic_score: float = 0.0
    effort_score: float = 0.0
    deficit_score: float = 0.0
    deadline_at: datetime | None = None
    recommended_minutes: int = 60
    reasons: list[str] = Field(default_factory=list)


class PedagogicalStepPayload(BaseModel):
    content_source: str = "internal_recommendation"
    course_id: UUID | None = None
    course_title: str | None = None
    level_id: UUID | None = None
    level_number: int | None = None
    level_title: str | None = None
    lesson_id: UUID | None = None
    lesson_title: str | None = None
    module_id: UUID | None = None
    module_title: str | None = None
    skill_id: UUID | None = None
    skill_name: str | None = None
    remediation_needed: bool = False
    remediation_reason: str | None = None
    blocked_prerequisites: list[str] = Field(default_factory=list)
    exercises_focus: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    recommended_session_type: str = "deep_work"
    next_step_summary: str = ""


class PlannedSessionProposal(BaseModel):
    slot_id: str
    title: str
    session_type: str = "deep_work"
    starts_at: datetime
    ends_at: datetime
    duration_minutes: int
    priority_source_type: str
    priority_source_id: str | None = None
    priority_score: float
    subject: str
    task_id: UUID | None = None
    project_id: UUID | None = None
    skill_id: UUID | None = None
    course_id: UUID | None = None
    lesson_id: UUID | None = None
    module_id: UUID | None = None
    slot_category: SlotCategory = SlotCategory.confirmed_availability
    rationale: str
    pedagogical_content: PedagogicalStepPayload = Field(default_factory=PedagogicalStepPayload)


class PlanArbitrageItem(BaseModel):
    source_type: str
    source_id: str | None = None
    title: str
    needed_minutes: int
    scheduled_minutes: int
    postponed_minutes: int
    reason: str
    deadline_at: datetime | None = None


class PlanLoadSummary(BaseModel):
    daily_minutes: dict[str, int] = Field(default_factory=dict)
    daily_cap_minutes: int = 240
    weekly_planned_minutes: int = 0
    weekly_cap_minutes: int = 600
    recovery_preserved_minutes: int = 0
    overloaded_days: list[str] = Field(default_factory=list)
    is_overloaded: bool = False


class PlanMissingInfoItem(BaseModel):
    field: str
    question: str
    why: str


class LearningPlanGenerateRequest(BaseModel):
    horizon_days: int = Field(default=7, ge=1, le=30)
    range_start: datetime | None = None
    timezone: str | None = Field(default=None, min_length=2, max_length=64)
    focus_subject: str | None = Field(default=None, max_length=120)
    exam_title: str | None = Field(default=None, max_length=160)
    exam_at: datetime | None = None
    weekly_hours_override: float | None = Field(default=None, gt=0.5, le=80)
    daily_max_minutes: int | None = Field(default=None, ge=30, le=600)
    preferred_session_minutes: int | None = Field(default=None, ge=25, le=180)
    min_session_minutes: int = Field(default=30, ge=15, le=120)
    buffer_minutes: int = Field(default=10, ge=0, le=45)
    include_potential_slots: bool = True
    create_missing_courses: bool = False
    idempotency_key: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=500)


class LearningPlanAdjustRequest(BaseModel):
    instruction: str = Field(..., min_length=2, max_length=500)
    horizon_days: int | None = Field(default=None, ge=1, le=30)
    range_start: datetime | None = None
    timezone: str | None = Field(default=None, min_length=2, max_length=64)
    keep_existing_applied: bool = True
    replace_future_planned: bool = True
    idempotency_key: str | None = Field(default=None, max_length=80)


class LearningPlanApplyRequest(BaseModel):
    replace_future_planned: bool = True
    selected_slot_ids: list[str] | None = None


class LearningPlanVersionResponse(BaseModel):
    id: UUID
    user_id: UUID
    version_number: int
    status: PlanVersionStatus
    horizon_days: int
    timezone: str
    rationale: str
    priorities: list[LearningPriorityItem] = Field(default_factory=list)
    planned_sessions: list[PlannedSessionProposal] = Field(default_factory=list)
    arbitrage_items: list[PlanArbitrageItem] = Field(default_factory=list)
    load_summary: PlanLoadSummary = Field(default_factory=PlanLoadSummary)
    availability_summary: AvailabilityComputationResponse | None = None
    missing_info: list[PlanMissingInfoItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    applied_event_ids: list[str] = Field(default_factory=list)
    applied_task_ids: list[str] = Field(default_factory=list)
    applied_course_ids: list[str] = Field(default_factory=list)
    parent_version_id: UUID | None = None
    applied_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    plan_payload: dict[str, Any] = Field(default_factory=dict)


class ScheduleValidityResponse(BaseModel):
    is_valid: bool
    expired_event_count: int = 0
    expired_task_count: int = 0
    overloaded_days: list[str] = Field(default_factory=list)
    missed_session_count: int = 0
    conflicting_event_ids: list[str] = Field(default_factory=list)
    stale_reasons: list[str] = Field(default_factory=list)
    recommendation: str = ""
