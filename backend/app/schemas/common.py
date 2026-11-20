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


class ScheduleEventSource(StrEnum):
    manual = "manual"
    timetable_import = "timetable_import"
    ai_proposal = "ai_proposal"


class TimetableFileFormat(StrEnum):
    pdf = "pdf"
    image = "image"
    excel = "excel"
    word = "word"


class TimetableImportStatus(StrEnum):
    pending_review = "pending_review"
    validated = "validated"
    cancelled = "cancelled"


class CourseSessionSubtype(StrEnum):
    cours = "cours"
    td = "td"
    tp = "tp"
    examen = "examen"
    autre = "autre"


class TimetableAnomalyType(StrEnum):
    missing_time = "missing_time"
    invalid_duration = "invalid_duration"
    missing_subject = "missing_subject"
    duplicate_course = "duplicate_course"
    overlap_conflict = "overlap_conflict"
    existing_calendar_conflict = "existing_calendar_conflict"
    uncertain_extraction = "uncertain_extraction"


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


class SkillAssessmentStatus(StrEnum):
    pending = "pending"
    submitted = "submitted"
    evaluated = "evaluated"
    needs_manual_review = "needs_manual_review"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class EvidenceVerificationStatus(StrEnum):
    declared = "declared"
    uploaded = "uploaded"
    inspected = "inspected"
    verified = "verified"
    approved = "approved"
    unreachable = "unreachable"
    rejected = "rejected"


class SkillEvaluationMode(StrEnum):
    automated = "automated"
    ai_assisted = "ai_assisted"
    manual_review = "manual_review"


class SkillAssessmentType(StrEnum):
    quiz = "quiz"
    practical_exercise = "practical_exercise"
    code_review = "code_review"
    explanation = "explanation"
    deliverable = "deliverable"
    mixed = "mixed"


class SkillEvaluatorType(StrEnum):
    pedagogical_engine = "pedagogical_engine"
    ai_copilot = "ai_copilot"
    self_rubric = "self_rubric"
    hybrid = "hybrid"


class ProjectStatus(StrEnum):
    planned = "planned"
    active = "active"
    paused = "paused"
    blocked = "blocked"
    completed = "completed"
    archived = "archived"


class ObjectiveCategory(StrEnum):
    learning_goal = "learning_goal"
    language = "language"
    framework = "framework"
    technology = "technology"
    spoken_language = "spoken_language"
    skill = "skill"
    project = "project"
    personal_project = "personal_project"
    professional_project = "professional_project"
    other = "other"


class ObjectiveStatus(StrEnum):
    planned = "planned"
    active = "active"
    paused = "paused"
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
    update_task = "update_task"
    park_task = "park_task"
    create_project = "create_project"
    update_project = "update_project"
    pause_project = "pause_project"
    create_schedule_event = "create_schedule_event"
    update_schedule_event = "update_schedule_event"
    archive_schedule_event = "archive_schedule_event"
    create_study_session = "create_study_session"
    create_skill = "create_skill"
    add_skill_evidence = "add_skill_evidence"
    propose_skill_assessment = "propose_skill_assessment"
    recommend_skill_progression = "recommend_skill_progression"
    create_learning_path = "create_learning_path"
    update_learning_path = "update_learning_path"
    create_personal_goal = "create_personal_goal"
    update_personal_goal = "update_personal_goal"
    plan_strategic_activity = "plan_strategic_activity"
    create_course = "create_course"
    update_preferences = "update_preferences"
    manage_availability_rule = "manage_availability_rule"
    generate_learning_plan = "generate_learning_plan"
    batch_actions = "batch_actions"


class CourseLanguage(StrEnum):
    fr = "fr"
    en = "en"
    bilingual = "bilingual"


class CourseStatus(StrEnum):
    draft = "draft"
    active = "active"
    paused = "paused"
    completed = "completed"


class CourseLevelStatus(StrEnum):
    locked = "locked"
    unlocked = "unlocked"
    in_progress = "in_progress"
    validated = "validated"


class CourseLessonStatus(StrEnum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"


class CourseResourceType(StrEnum):
    documentation = "documentation"
    video = "video"
    article = "article"
    book = "book"
    interactive = "interactive"


class CourseSubmissionKind(StrEnum):
    exercise = "exercise"
    project = "project"


class CourseSubmissionStatus(StrEnum):
    submitted = "submitted"
    evaluated = "evaluated"


class StrategicDecision(StrEnum):
    acceptable = "ACCEPTABLE"
    acceptable_with_conditions = "ACCEPTABLE_WITH_CONDITIONS"
    not_recommended = "NOT_RECOMMENDED"


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
    goals = "goals"
    memory = "memory"
    weekly = "weekly"


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
