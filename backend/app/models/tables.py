from datetime import datetime, timezone
from typing import Any
from uuid import UUID
from sqlalchemy import (
    Boolean,
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TypeDecorator,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class UTCDateTime(TypeDecorator[datetime]):
    """Stocke en TIMESTAMPTZ sur PostgreSQL et garantit des datetimes UTC aware sur SQLite."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


JsonPayload = JSON().with_variant(JSONB(), "postgresql")


class ProfileTable(Base):
    __tablename__ = "profiles"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(80), nullable=False, default="Africa/Dakar")
    active_priority_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    active_priority_task_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    active_priority_project_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    preferences: Mapped[dict[str, Any]] = mapped_column(JsonPayload, nullable=False, default=dict)
    ai_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class TaskTable(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('todo', 'in_progress', 'done', 'cancelled', 'parked')",
            name="ck_tasks_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'critical')",
            name="ck_tasks_priority",
        ),
        Index("ix_tasks_user_id", "user_id"),
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_due_at", "due_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="todo")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    due_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    proposal_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    project_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    module_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class TimetableImportTable(Base):
    __tablename__ = "timetable_imports"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_review', 'validated', 'cancelled')",
            name="ck_timetable_imports_status",
        ),
        CheckConstraint(
            "file_format IN ('pdf', 'image', 'excel', 'word')",
            name="ck_timetable_imports_format",
        ),
        CheckConstraint(
            "file_size_bytes > 0",
            name="ck_timetable_imports_size",
        ),
        Index("ix_timetable_imports_user_id", "user_id"),
        Index("ix_timetable_imports_status", "status"),
        Index("ix_timetable_imports_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_format: Mapped[str] = mapped_column(String(20), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_preview_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending_review")
    valid_from: Mapped[str | None] = mapped_column(String(10), nullable=True)
    valid_until: Mapped[str | None] = mapped_column(String(10), nullable=True)
    extracted_courses: Mapped[list[dict[str, Any]]] = mapped_column(
        JsonPayload, nullable=False, default=list
    )
    anomalies: Mapped[list[dict[str, Any]]] = mapped_column(
        JsonPayload, nullable=False, default=list
    )
    warnings: Mapped[list[str]] = mapped_column(JsonPayload, nullable=False, default=list)
    created_events_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_duplicates_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    replaced_events_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    validated_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class ScheduleEventTable(Base):
    __tablename__ = "schedule_events"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="ck_schedule_events_range"),
        Index("ix_schedule_user_id", "user_id"),
        Index("ix_schedule_starts_at", "starts_at"),
        Index("ix_schedule_import_id", "import_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="course")
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    import_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("timetable_imports.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_subtype: Mapped[str | None] = mapped_column(String(20), nullable=True)
    teacher: Mapped[str | None] = mapped_column(String(120), nullable=True)
    room: Mapped[str | None] = mapped_column(String(100), nullable=True)
    group_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class StudySessionTable(Base):
    __tablename__ = "study_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('in_progress', 'completed', 'cancelled')",
            name="ck_study_sessions_status",
        ),
        CheckConstraint(
            "ended_at IS NULL OR ended_at > started_at",
            name="ck_study_sessions_range",
        ),
        Index("ix_sessions_user_id", "user_id"),
        Index("ix_sessions_status", "status"),
        Index("ix_sessions_started_at", "started_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="in_progress")
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    project_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    module_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    lesson_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    skill_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class LearningPathTable(Base):
    __tablename__ = "learning_paths"
    __table_args__ = (
        CheckConstraint(
            "status IN ('not_started', 'active', 'paused', 'completed')",
            name="ck_learning_paths_status",
        ),
        Index("ix_learning_paths_user_id", "user_id"),
        Index("ix_learning_paths_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_started")
    goal: Mapped[str] = mapped_column(String(300), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class LearningModuleTable(Base):
    __tablename__ = "learning_modules"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_learning_modules_position"),
        CheckConstraint(
            "status IN ('not_started', 'active', 'paused', 'completed')",
            name="ck_learning_modules_status",
        ),
        Index("ix_learning_modules_user_id", "user_id"),
        Index("ix_learning_modules_path_id", "path_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    path_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_paths.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_started")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class LessonTable(Base):
    __tablename__ = "lessons"
    __table_args__ = (
        CheckConstraint("position >= 0", name="ck_lessons_position"),
        CheckConstraint(
            "status IN ('not_started', 'active', 'paused', 'completed')",
            name="ck_lessons_status",
        ),
        Index("ix_lessons_user_id", "user_id"),
        Index("ix_lessons_module_id", "module_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    module_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_modules.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(140), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    resource_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_started")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class SkillTable(Base):
    __tablename__ = "skills"
    __table_args__ = (
        CheckConstraint(
            "current_level >= 0 AND current_level <= 5",
            name="ck_skills_current_level",
        ),
        CheckConstraint(
            "target_level IS NULL OR (target_level >= 0 AND target_level <= 5)",
            name="ck_skills_target_level",
        ),
        Index("ix_skills_user_id", "user_id"),
        Index("ix_skills_domain", "domain"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    domain: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    target_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_assessed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class SkillEvidenceTable(Base):
    __tablename__ = "skill_evidence"
    __table_args__ = (
        CheckConstraint(
            "type IN ('exercise', 'project', 'code', 'assessment', 'deliverable', 'other')",
            name="ck_skill_evidence_type",
        ),
        Index("ix_skill_evidence_user_id", "user_id"),
        Index("ix_skill_evidence_skill_id", "skill_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    skill_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="exercise")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reference_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    result: Mapped[str | None] = mapped_column(String(200), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class SkillAssessmentTable(Base):
    __tablename__ = "skill_assessments"
    __table_args__ = (
        CheckConstraint(
            "starting_level >= 0 AND starting_level <= 5",
            name="ck_skill_assessments_starting_level",
        ),
        CheckConstraint(
            "target_level >= 1 AND target_level <= 5",
            name="ck_skill_assessments_target_level",
        ),
        CheckConstraint(
            "proposed_level IS NULL OR (proposed_level >= 0 AND proposed_level <= 5)",
            name="ck_skill_assessments_proposed_level",
        ),
        CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)",
            name="ck_skill_assessments_score",
        ),
        CheckConstraint(
            "hints_revealed_count >= 0",
            name="ck_skill_assessments_hints_revealed",
        ),
        CheckConstraint(
            "status IN ('pending', 'submitted', 'evaluated', 'approved', 'rejected', 'cancelled')",
            name="ck_skill_assessments_status",
        ),
        CheckConstraint(
            "assessment_type IN ('quiz', 'practical_exercise', 'code_review', 'explanation', 'deliverable', 'mixed')",
            name="ck_skill_assessments_type",
        ),
        Index("ix_skill_assessments_user_id", "user_id"),
        Index("ix_skill_assessments_skill_id", "skill_id"),
        Index("ix_skill_assessments_status", "status"),
        Index("ix_skill_assessments_user_skill", "user_id", "skill_id"),
        Index("ix_skill_assessments_path_id", "path_id"),
        Index("ix_skill_assessments_module_id", "module_id"),
        Index("ix_skill_assessments_lesson_id", "lesson_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    skill_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
    )
    path_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_paths.id", ondelete="SET NULL"),
        nullable=True,
    )
    module_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_modules.id", ondelete="SET NULL"),
        nullable=True,
    )
    lesson_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("lessons.id", ondelete="SET NULL"),
        nullable=True,
    )
    assessment_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="practical_exercise"
    )
    starting_level: Mapped[int] = mapped_column(Integer, nullable=False)
    target_level: Mapped[int] = mapped_column(Integer, nullable=False)
    proposed_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    prompt_title: Mapped[str] = mapped_column(String(180), nullable=False)
    prompt_instructions: Mapped[str] = mapped_column(Text, nullable=False)
    hints: Mapped[list[str]] = mapped_column(JsonPayload, nullable=False, default=list)
    hints_revealed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    submission_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    submission_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    submission_reference_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    evidence_ids: Mapped[list[str]] = mapped_column(JsonPayload, nullable=False, default=list)
    criteria: Mapped[list[dict[str, Any]]] = mapped_column(JsonPayload, nullable=False, default=list)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    mastered_points: Mapped[list[str]] = mapped_column(JsonPayload, nullable=False, default=list)
    gaps_identified: Mapped[list[str]] = mapped_column(JsonPayload, nullable=False, default=list)
    remediation_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_verification_warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluator_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pedagogical_engine"
    )
    evaluator_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_level_delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    evaluated_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class ProjectTable(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "status IN ('planned', 'active', 'blocked', 'completed', 'archived')",
            name="ck_projects_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'critical')",
            name="ck_projects_priority",
        ),
        Index("ix_projects_user_id", "user_id"),
        Index("ix_projects_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    goal: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="planned")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    next_action: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    deliverables: Mapped[list[str] | None] = mapped_column(JsonPayload, nullable=True)
    target_date: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class AiConversationTable(Base):
    __tablename__ = "ai_conversations"
    __table_args__ = (Index("ix_ai_conversations_user_id", "user_id"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class AiMessageTable(Base):
    __tablename__ = "ai_messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant', 'system')",
            name="ck_ai_messages_role",
        ),
        Index("ix_ai_messages_user_id", "user_id"),
        Index("ix_ai_messages_conversation_id", "conversation_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    conversation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JsonPayload,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class AiActionProposalTable(Base):
    __tablename__ = "ai_action_proposals"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected', 'expired', 'executed', 'failed')",
            name="ck_ai_action_proposals_status",
        ),
        Index("ix_ai_action_proposals_user_id", "user_id"),
        Index("ix_ai_action_proposals_conversation_id", "conversation_id"),
        Index("ix_ai_action_proposals_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    conversation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonPayload, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    execution_result: Mapped[dict[str, Any] | None] = mapped_column(JsonPayload, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)


class AiReportTable(Base):
    __tablename__ = "ai_reports"
    __table_args__ = (
        CheckConstraint(
            "type IN ('daily_briefing', 'weekly_review')",
            name="ck_ai_reports_type",
        ),
        Index("ix_ai_reports_user_id", "user_id"),
        Index("ix_ai_reports_type", "type"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    period_start: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    period_end: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JsonPayload,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class CourseTable(Base):
    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint(
            "language IN ('fr', 'en', 'bilingual')",
            name="ck_courses_language",
        ),
        CheckConstraint(
            "current_level >= 1 AND current_level <= 5",
            name="ck_courses_current_level",
        ),
        CheckConstraint(
            "total_levels >= 1 AND total_levels <= 5",
            name="ck_courses_total_levels",
        ),
        CheckConstraint(
            "current_level <= total_levels",
            name="ck_courses_level_bounds",
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'paused', 'completed')",
            name="ck_courses_status",
        ),
        Index("ix_courses_user_id", "user_id"),
        Index("ix_courses_status", "status"),
        Index("ix_courses_skill_id", "skill_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    subject: Mapped[str] = mapped_column(String(120), nullable=False)
    domain: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="fr")
    current_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    total_levels: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    skill_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("skills.id", ondelete="SET NULL"),
        nullable=True,
    )
    learning_path_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("learning_paths.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class CourseLevelTable(Base):
    __tablename__ = "course_levels"
    __table_args__ = (
        CheckConstraint(
            "level_number >= 1 AND level_number <= 5",
            name="ck_course_levels_number",
        ),
        CheckConstraint(
            "status IN ('locked', 'unlocked', 'in_progress', 'validated')",
            name="ck_course_levels_status",
        ),
        Index("ix_course_levels_user_id", "user_id"),
        Index("ix_course_levels_course_id", "course_id"),
        Index("ix_course_levels_course_num", "course_id", "level_number"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    course_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    level_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    objectives: Mapped[list[str]] = mapped_column(JsonPayload, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="locked")
    content_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    project_title: Mapped[str | None] = mapped_column(String(180), nullable=True)
    project_brief: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_deliverables: Mapped[list[str]] = mapped_column(JsonPayload, nullable=False, default=list)
    project_rubric: Mapped[list[dict[str, Any]]] = mapped_column(
        JsonPayload, nullable=False, default=list
    )
    validated_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class CourseLessonTable(Base):
    __tablename__ = "course_lessons"
    __table_args__ = (
        CheckConstraint("position >= 1", name="ck_course_lessons_position"),
        CheckConstraint(
            "estimated_minutes >= 5 AND estimated_minutes <= 240",
            name="ck_course_lessons_minutes",
        ),
        CheckConstraint(
            "status IN ('not_started', 'in_progress', 'completed')",
            name="ck_course_lessons_status",
        ),
        Index("ix_course_lessons_user_id", "user_id"),
        Index("ix_course_lessons_course_id", "course_id"),
        Index("ix_course_lessons_level_id", "level_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    course_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    level_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("course_levels.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(300), nullable=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=25)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    code_examples: Mapped[list[dict[str, Any]]] = mapped_column(
        JsonPayload, nullable=False, default=list
    )
    exercises: Mapped[list[dict[str, Any]]] = mapped_column(
        JsonPayload, nullable=False, default=list
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="not_started")
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class CourseResourceTable(Base):
    __tablename__ = "course_resources"
    __table_args__ = (
        CheckConstraint(
            "resource_type IN ('documentation', 'video', 'article', 'book', 'interactive')",
            name="ck_course_resources_type",
        ),
        CheckConstraint(
            "language IN ('fr', 'en')",
            name="ck_course_resources_language",
        ),
        Index("ix_course_resources_user_id", "user_id"),
        Index("ix_course_resources_course_id", "course_id"),
        Index("ix_course_resources_level_id", "level_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    course_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    level_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("course_levels.id", ondelete="CASCADE"),
        nullable=True,
    )
    lesson_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("course_lessons.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="fr")
    is_official: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(400), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class CourseSubmissionTable(Base):
    __tablename__ = "course_submissions"
    __table_args__ = (
        CheckConstraint(
            "submission_kind IN ('exercise', 'project')",
            name="ck_course_submissions_kind",
        ),
        CheckConstraint(
            "status IN ('submitted', 'evaluated')",
            name="ck_course_submissions_status",
        ),
        CheckConstraint(
            "score IS NULL OR (score >= 0 AND score <= 100)",
            name="ck_course_submissions_score",
        ),
        Index("ix_course_submissions_user_id", "user_id"),
        Index("ix_course_submissions_course_id", "course_id"),
        Index("ix_course_submissions_level_id", "level_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    course_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    level_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("course_levels.id", ondelete="CASCADE"),
        nullable=False,
    )
    lesson_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("course_lessons.id", ondelete="SET NULL"),
        nullable=True,
    )
    submission_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    exercise_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="evaluated")
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    criteria_results: Mapped[list[dict[str, Any]]] = mapped_column(
        JsonPayload, nullable=False, default=list
    )
    feedback_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    strengths: Mapped[list[str]] = mapped_column(JsonPayload, nullable=False, default=list)
    improvements: Mapped[list[str]] = mapped_column(JsonPayload, nullable=False, default=list)
    next_step_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class UserAccountTable(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("token_version >= 1", name="ck_users_token_version"),
        Index("ix_users_email", "email", unique=True),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
