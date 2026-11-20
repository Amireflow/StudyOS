from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import AfterValidator, BaseModel


def ensure_utc_datetime(value: datetime) -> datetime:
    """Exige une date avec fuseau explicite et la normalise en UTC."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("La date doit inclure un fuseau horaire explicite (ex. Z ou +00:00).")
    return value.astimezone(timezone.utc)


def validate_iana_timezone(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Le fuseau horaire ne peut pas être vide.")
    try:
        ZoneInfo(cleaned)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"Fuseau horaire IANA invalide : {cleaned}") from exc
    return cleaned


def normalize_optional_text(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > max_length:
        raise ValueError(f"Ce champ ne doit pas dépasser {max_length} caractères.")
    return cleaned


def validate_optional_http_url(value: str | None) -> str | None:
    """Normalise une URL facultative et impose le schéma http:// ou https://."""
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > 500:
        raise ValueError("L’URL ne doit pas dépasser 500 caractères.")
    lowered = cleaned.lower()
    if not (lowered.startswith("http://") or lowered.startswith("https://")):
        raise ValueError("L’URL doit commencer par http:// ou https://.")
    return cleaned


UtcDatetime = Annotated[datetime, AfterValidator(ensure_utc_datetime)]


class TaskStatus(StrEnum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"
    cancelled = "cancelled"
    parked = "parked"


class TaskPriority(StrEnum):
    low = "low"
    normal = "normal"
    high = "high"
    critical = "critical"


class TaskSource(StrEnum):
    manual = "manual"
    ai_proposal = "ai_proposal"


class ScheduleEventType(StrEnum):
    course = "course"
    learning = "learning"
    project = "project"
    personal = "personal"
    other = "other"


class SessionStatus(StrEnum):
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class LearningStatus(StrEnum):
    not_started = "not_started"
    active = "active"
    paused = "paused"
    completed = "completed"


class SkillEvidenceType(StrEnum):
    exercise = "exercise"
    project = "project"
    code = "code"
    assessment = "assessment"
    deliverable = "deliverable"
    other = "other"


class ProjectStatus(StrEnum):
    planned = "planned"
    active = "active"
    blocked = "blocked"
    completed = "completed"
    archived = "archived"


class AiMessageRole(StrEnum):
    user = "user"
    assistant = "assistant"
    system = "system"


class ProposalStatus(StrEnum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    expired = "expired"
    executed = "executed"
    failed = "failed"


class AiActionType(StrEnum):
    create_task = "create_task"
    park_task = "park_task"
    create_schedule_event = "create_schedule_event"
    add_skill_evidence = "add_skill_evidence"
    update_skill_level = "update_skill_level"


class AiReportType(StrEnum):
    daily_briefing = "daily_briefing"
    weekly_review = "weekly_review"


class AiContextScope(StrEnum):
    auto = "auto"
    today = "today"
    tasks = "tasks"
    schedule = "schedule"
    learning = "learning"
    skills = "skills"
    projects = "projects"
    weekly = "weekly"


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
