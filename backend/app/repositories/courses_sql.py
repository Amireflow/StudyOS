from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.tables import (
    CourseLessonTable,
    CourseLevelTable,
    CourseResourceTable,
    CourseSubmissionTable,
    CourseTable,
)
from app.repositories.learning_sql import _delete_owned_row, _get_owned_row, _upsert_owned_row
from app.schemas.common import (
    CourseLanguage,
    CourseLessonStatus,
    CourseLevelStatus,
    CourseResourceType,
    CourseStatus,
    CourseSubmissionKind,
    CourseSubmissionStatus,
)


class CourseRecord(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    subject: str
    domain: str
    description: str | None = None
    language: CourseLanguage = CourseLanguage.fr
    current_level: int = 1
    total_levels: int = 3
    status: CourseStatus = CourseStatus.active
    skill_id: UUID | None = None
    learning_path_id: UUID | None = None
    generation_source: str = "curated_local"
    generation_model: str | None = None
    created_at: datetime
    updated_at: datetime


class CourseLevelRecord(BaseModel):
    id: UUID
    user_id: UUID
    course_id: UUID
    level_number: int
    title: str
    summary: str = ""
    objectives: list[str] = []
    status: CourseLevelStatus = CourseLevelStatus.locked
    content_generated: bool = False
    project_title: str | None = None
    project_brief: str | None = None
    project_deliverables: list[str] = []
    project_rubric: list[dict[str, Any]] = []
    previous_versions: list[dict[str, Any]] = []
    revision: int = 1
    generation_source: str = "curated_local"
    validated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CourseLessonRecord(BaseModel):
    id: UUID
    user_id: UUID
    course_id: UUID
    level_id: UUID
    position: int = 1
    title: str
    summary: str | None = None
    estimated_minutes: int = 25
    content_markdown: str
    code_examples: list[dict[str, Any]] = []
    exercises: list[dict[str, Any]] = []
    status: CourseLessonStatus = CourseLessonStatus.not_started
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CourseResourceRecord(BaseModel):
    id: UUID
    user_id: UUID
    course_id: UUID
    level_id: UUID | None = None
    lesson_id: UUID | None = None
    title: str
    url: str
    resource_type: CourseResourceType = CourseResourceType.documentation
    language: str = "fr"
    is_official: bool = False
    source_name: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class CourseSubmissionRecord(BaseModel):
    id: UUID
    user_id: UUID
    course_id: UUID
    level_id: UUID
    lesson_id: UUID | None = None
    submission_kind: CourseSubmissionKind = CourseSubmissionKind.exercise
    exercise_id: str | None = None
    title: str
    answer_text: str
    submitted_code: str | None = None
    reference_url: str | None = None
    status: CourseSubmissionStatus = CourseSubmissionStatus.evaluated
    score: int | None = None
    passed: bool | None = None
    criteria_results: list[dict[str, Any]] = []
    feedback_markdown: str | None = None
    strengths: list[str] = []
    improvements: list[str] = []
    next_step_hint: str | None = None
    attempt_number: int = 1
    evaluation_mode: str = "deterministic"
    manual_review_required: bool = False
    static_analysis: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


def _to_course_record(row: CourseTable) -> CourseRecord:
    return CourseRecord(
        id=row.id,
        user_id=row.user_id,
        title=row.title,
        subject=row.subject,
        domain=row.domain,
        description=row.description,
        language=CourseLanguage(row.language),
        current_level=row.current_level,
        total_levels=row.total_levels,
        status=CourseStatus(row.status),
        skill_id=row.skill_id,
        learning_path_id=row.learning_path_id,
        generation_source=getattr(row, "generation_source", "curated_local") or "curated_local",
        generation_model=getattr(row, "generation_model", None),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_level_record(row: CourseLevelTable) -> CourseLevelRecord:
    return CourseLevelRecord(
        id=row.id,
        user_id=row.user_id,
        course_id=row.course_id,
        level_number=row.level_number,
        title=row.title,
        summary=row.summary,
        objectives=list(row.objectives or []),
        status=CourseLevelStatus(row.status),
        content_generated=row.content_generated,
        project_title=row.project_title,
        project_brief=row.project_brief,
        project_deliverables=list(row.project_deliverables or []),
        project_rubric=[dict(item) for item in (row.project_rubric or [])],
        previous_versions=[dict(item) for item in (getattr(row, "previous_versions", None) or [])],
        revision=int(getattr(row, "revision", 1) or 1),
        generation_source=getattr(row, "generation_source", "curated_local") or "curated_local",
        validated_at=row.validated_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_lesson_record(row: CourseLessonTable) -> CourseLessonRecord:
    return CourseLessonRecord(
        id=row.id,
        user_id=row.user_id,
        course_id=row.course_id,
        level_id=row.level_id,
        position=row.position,
        title=row.title,
        summary=row.summary,
        estimated_minutes=row.estimated_minutes,
        content_markdown=row.content_markdown,
        code_examples=[dict(item) for item in (row.code_examples or [])],
        exercises=[dict(item) for item in (row.exercises or [])],
        status=CourseLessonStatus(row.status),
        completed_at=row.completed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_resource_record(row: CourseResourceTable) -> CourseResourceRecord:
    return CourseResourceRecord(
        id=row.id,
        user_id=row.user_id,
        course_id=row.course_id,
        level_id=row.level_id,
        lesson_id=row.lesson_id,
        title=row.title,
        url=row.url,
        resource_type=CourseResourceType(row.resource_type),
        language=row.language,
        is_official=row.is_official,
        source_name=row.source_name,
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_submission_record(row: CourseSubmissionTable) -> CourseSubmissionRecord:
    return CourseSubmissionRecord(
        id=row.id,
        user_id=row.user_id,
        course_id=row.course_id,
        level_id=row.level_id,
        lesson_id=row.lesson_id,
        submission_kind=CourseSubmissionKind(row.submission_kind),
        exercise_id=row.exercise_id,
        title=row.title,
        answer_text=row.answer_text,
        submitted_code=row.submitted_code,
        reference_url=row.reference_url,
        status=CourseSubmissionStatus(row.status),
        score=row.score,
        passed=row.passed,
        criteria_results=[dict(item) for item in (row.criteria_results or [])],
        feedback_markdown=row.feedback_markdown,
        strengths=list(row.strengths or []),
        improvements=list(row.improvements or []),
        next_step_hint=row.next_step_hint,
        attempt_number=int(getattr(row, "attempt_number", 1) or 1),
        evaluation_mode=getattr(row, "evaluation_mode", "deterministic") or "deterministic",
        manual_review_required=bool(getattr(row, "manual_review_required", False)),
        static_analysis=getattr(row, "static_analysis", None),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlCourseRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_courses(self, user_id: UUID) -> list[CourseRecord]:
        stmt = (
            select(CourseTable)
            .where(CourseTable.user_id == user_id)
            .order_by(CourseTable.updated_at.desc())
        )
        return [_to_course_record(row) for row in self._db.scalars(stmt)]

    def get_course(self, user_id: UUID, course_id: UUID) -> CourseRecord | None:
        row = _get_owned_row(self._db, CourseTable, course_id, user_id)
        return _to_course_record(row) if row is not None else None

    def save_course(self, record: CourseRecord) -> CourseRecord:
        saved = _upsert_owned_row(
            self._db,
            CourseTable,
            record.id,
            record.user_id,
            {
                "id": record.id,
                "user_id": record.user_id,
                "title": record.title,
                "subject": record.subject,
                "domain": record.domain,
                "description": record.description,
                "language": record.language.value,
                "current_level": record.current_level,
                "total_levels": record.total_levels,
                "status": record.status.value,
                "skill_id": record.skill_id,
                "learning_path_id": record.learning_path_id,
                "generation_source": record.generation_source,
                "generation_model": record.generation_model,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            },
        )
        return _to_course_record(saved)

    def delete_course(self, user_id: UUID, course_id: UUID) -> bool:
        return _delete_owned_row(self._db, CourseTable, course_id, user_id)

    def list_levels(self, user_id: UUID, *, course_id: UUID | None = None) -> list[CourseLevelRecord]:
        stmt = select(CourseLevelTable).where(CourseLevelTable.user_id == user_id)
        if course_id is not None:
            stmt = stmt.where(CourseLevelTable.course_id == course_id)
        stmt = stmt.order_by(CourseLevelTable.level_number.asc())
        return [_to_level_record(row) for row in self._db.scalars(stmt)]

    def get_level(self, user_id: UUID, level_id: UUID) -> CourseLevelRecord | None:
        row = _get_owned_row(self._db, CourseLevelTable, level_id, user_id)
        return _to_level_record(row) if row is not None else None

    def save_level(self, record: CourseLevelRecord) -> CourseLevelRecord:
        saved = _upsert_owned_row(
            self._db,
            CourseLevelTable,
            record.id,
            record.user_id,
            {
                "id": record.id,
                "user_id": record.user_id,
                "course_id": record.course_id,
                "level_number": record.level_number,
                "title": record.title,
                "summary": record.summary,
                "objectives": record.objectives,
                "status": record.status.value,
                "content_generated": record.content_generated,
                "project_title": record.project_title,
                "project_brief": record.project_brief,
                "project_deliverables": record.project_deliverables,
                "project_rubric": record.project_rubric,
                "previous_versions": record.previous_versions,
                "revision": record.revision,
                "generation_source": record.generation_source,
                "validated_at": record.validated_at,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            },
        )
        return _to_level_record(saved)

    def list_lessons(
        self,
        user_id: UUID,
        *,
        course_id: UUID | None = None,
        level_id: UUID | None = None,
    ) -> list[CourseLessonRecord]:
        stmt = select(CourseLessonTable).where(CourseLessonTable.user_id == user_id)
        if course_id is not None:
            stmt = stmt.where(CourseLessonTable.course_id == course_id)
        if level_id is not None:
            stmt = stmt.where(CourseLessonTable.level_id == level_id)
        stmt = stmt.order_by(CourseLessonTable.position.asc())
        return [_to_lesson_record(row) for row in self._db.scalars(stmt)]

    def get_lesson(self, user_id: UUID, lesson_id: UUID) -> CourseLessonRecord | None:
        row = _get_owned_row(self._db, CourseLessonTable, lesson_id, user_id)
        return _to_lesson_record(row) if row is not None else None

    def save_lesson(self, record: CourseLessonRecord) -> CourseLessonRecord:
        saved = _upsert_owned_row(
            self._db,
            CourseLessonTable,
            record.id,
            record.user_id,
            {
                "id": record.id,
                "user_id": record.user_id,
                "course_id": record.course_id,
                "level_id": record.level_id,
                "position": record.position,
                "title": record.title,
                "summary": record.summary,
                "estimated_minutes": record.estimated_minutes,
                "content_markdown": record.content_markdown,
                "code_examples": record.code_examples,
                "exercises": record.exercises,
                "status": record.status.value,
                "completed_at": record.completed_at,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            },
        )
        return _to_lesson_record(saved)

    def list_resources(
        self,
        user_id: UUID,
        *,
        course_id: UUID | None = None,
        level_id: UUID | None = None,
    ) -> list[CourseResourceRecord]:
        stmt = select(CourseResourceTable).where(CourseResourceTable.user_id == user_id)
        if course_id is not None:
            stmt = stmt.where(CourseResourceTable.course_id == course_id)
        if level_id is not None:
            stmt = stmt.where(CourseResourceTable.level_id == level_id)
        stmt = stmt.order_by(CourseResourceTable.is_official.desc(), CourseResourceTable.created_at.asc())
        return [_to_resource_record(row) for row in self._db.scalars(stmt)]

    def get_resource(self, user_id: UUID, resource_id: UUID) -> CourseResourceRecord | None:
        row = _get_owned_row(self._db, CourseResourceTable, resource_id, user_id)
        return _to_resource_record(row) if row is not None else None

    def save_resource(self, record: CourseResourceRecord) -> CourseResourceRecord:
        saved = _upsert_owned_row(
            self._db,
            CourseResourceTable,
            record.id,
            record.user_id,
            {
                "id": record.id,
                "user_id": record.user_id,
                "course_id": record.course_id,
                "level_id": record.level_id,
                "lesson_id": record.lesson_id,
                "title": record.title,
                "url": record.url,
                "resource_type": record.resource_type.value,
                "language": record.language,
                "is_official": record.is_official,
                "source_name": record.source_name,
                "notes": record.notes,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            },
        )
        return _to_resource_record(saved)

    def delete_resource(self, user_id: UUID, resource_id: UUID) -> bool:
        return _delete_owned_row(self._db, CourseResourceTable, resource_id, user_id)

    def list_submissions(
        self,
        user_id: UUID,
        *,
        course_id: UUID | None = None,
        level_id: UUID | None = None,
    ) -> list[CourseSubmissionRecord]:
        stmt = select(CourseSubmissionTable).where(CourseSubmissionTable.user_id == user_id)
        if course_id is not None:
            stmt = stmt.where(CourseSubmissionTable.course_id == course_id)
        if level_id is not None:
            stmt = stmt.where(CourseSubmissionTable.level_id == level_id)
        stmt = stmt.order_by(CourseSubmissionTable.created_at.desc())
        return [_to_submission_record(row) for row in self._db.scalars(stmt)]

    def save_submission(self, record: CourseSubmissionRecord) -> CourseSubmissionRecord:
        saved = _upsert_owned_row(
            self._db,
            CourseSubmissionTable,
            record.id,
            record.user_id,
            {
                "id": record.id,
                "user_id": record.user_id,
                "course_id": record.course_id,
                "level_id": record.level_id,
                "lesson_id": record.lesson_id,
                "submission_kind": record.submission_kind.value,
                "exercise_id": record.exercise_id,
                "title": record.title,
                "answer_text": record.answer_text,
                "submitted_code": record.submitted_code,
                "reference_url": record.reference_url,
                "status": record.status.value,
                "score": record.score,
                "passed": record.passed,
                "criteria_results": record.criteria_results,
                "feedback_markdown": record.feedback_markdown,
                "strengths": record.strengths,
                "improvements": record.improvements,
                "next_step_hint": record.next_step_hint,
                "attempt_number": record.attempt_number,
                "evaluation_mode": record.evaluation_mode,
                "manual_review_required": record.manual_review_required,
                "static_analysis": record.static_analysis,
                "created_at": record.created_at,
                "updated_at": record.updated_at,
            },
        )
        return _to_submission_record(saved)

    def delete_lessons_for_level(self, user_id: UUID, level_id: UUID) -> int:
        from sqlalchemy import delete as sa_delete

        res = self._db.execute(
            sa_delete(CourseLessonTable).where(
                CourseLessonTable.user_id == user_id,
                CourseLessonTable.level_id == level_id,
            )
        )
        self._db.commit()
        return int(res.rowcount or 0)
