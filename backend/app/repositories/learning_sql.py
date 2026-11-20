from datetime import datetime
from typing import Any, TypeVar
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session
from app.models.tables import (
    LearningModuleTable,
    LearningPathTable,
    LessonTable,
    PersonalGoalTable,
    ProjectTable,
    SkillAssessmentTable,
    SkillEvidenceTable,
    SkillTable,
    StudySessionTable,
    TaskTable,
)
from app.core.errors import AppError
from app.schemas.common import (
    EvidenceVerificationStatus,
    LearningStatus,
    ObjectiveCategory,
    ObjectiveStatus,
    ProjectStatus,
    SkillAssessmentStatus,
    SkillAssessmentType,
    SkillEvaluationMode,
    SkillEvaluatorType,
    SkillEvidenceType,
    TaskPriority,
)

TableT = TypeVar("TableT")


class LearningPathRecord(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    description: str | None = None
    status: LearningStatus = LearningStatus.not_started
    goal: str
    created_at: datetime
    updated_at: datetime


class LearningModuleRecord(BaseModel):
    id: UUID
    user_id: UUID
    path_id: UUID
    title: str
    description: str | None = None
    position: int = 0
    status: LearningStatus = LearningStatus.not_started
    created_at: datetime
    updated_at: datetime


class LessonRecord(BaseModel):
    id: UUID
    user_id: UUID
    module_id: UUID
    title: str
    content: str | None = None
    resource_url: str | None = None
    position: int = 0
    status: LearningStatus = LearningStatus.not_started
    created_at: datetime
    updated_at: datetime


class SkillRecord(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    domain: str
    description: str | None = None
    current_level: int = 0
    target_level: int | None = None
    last_assessed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SkillEvidenceRecord(BaseModel):
    id: UUID
    user_id: UUID
    skill_id: UUID
    type: SkillEvidenceType = SkillEvidenceType.exercise
    description: str
    reference_url: str | None = None
    result: str | None = None
    verification_status: EvidenceVerificationStatus = EvidenceVerificationStatus.declared
    inspection_metadata: dict[str, Any] = {}
    inspected_at: datetime | None = None
    is_locked: bool = False
    observed_at: datetime
    created_at: datetime
    updated_at: datetime


class SkillAssessmentRecord(BaseModel):
    id: UUID
    user_id: UUID
    skill_id: UUID
    path_id: UUID | None = None
    module_id: UUID | None = None
    lesson_id: UUID | None = None
    assessment_type: SkillAssessmentType = SkillAssessmentType.practical_exercise
    starting_level: int
    target_level: int
    proposed_level: int | None = None
    status: SkillAssessmentStatus = SkillAssessmentStatus.pending
    prompt_title: str
    prompt_instructions: str
    hints: list[str] = []
    hints_revealed_count: int = 0
    submission_text: str | None = None
    submission_code: str | None = None
    submission_reference_url: str | None = None
    evidence_ids: list[str] = []
    criteria: list[dict[str, Any]] = []
    rubric_version: str = "rubric-v2"
    evaluator_version: str = "eval-v2"
    evaluation_mode: SkillEvaluationMode = SkillEvaluationMode.automated
    manual_review_required: bool = False
    rubric_snapshot: list[dict[str, Any]] = []
    evidence_snapshot: list[dict[str, Any]] = []
    reviewed_by: str | None = None
    score: int | None = None
    passed: bool | None = None
    feedback: str | None = None
    mastered_points: list[str] = []
    gaps_identified: list[str] = []
    remediation_recommendation: str | None = None
    external_verification_warning: str | None = None
    evaluator_type: SkillEvaluatorType = SkillEvaluatorType.pedagogical_engine
    evaluator_name: str | None = None
    decision_reason: str | None = None
    applied_level_delta: int | None = None
    submitted_at: datetime | None = None
    evaluated_at: datetime | None = None
    validated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ProjectRecord(BaseModel):
    id: UUID
    user_id: UUID
    category: str = "project"
    name: str
    description: str | None = None
    goal: str
    status: ProjectStatus = ProjectStatus.planned
    priority: TaskPriority = TaskPriority.normal
    motivation: str | None = None
    start_date: datetime | None = None
    weekly_target_minutes: int = 180
    next_action: str = ""
    steps: list[dict[str, Any]] = []
    deliverables: list[str] | None = None
    success_criteria: list[str] = []
    progress_history: list[dict[str, Any]] = []
    target_date: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PersonalGoalRecord(BaseModel):
    id: UUID
    user_id: UUID
    category: ObjectiveCategory = ObjectiveCategory.learning_goal
    title: str
    description: str | None = None
    goal: str
    current_level: int | None = None
    target_level: int | None = None
    priority: TaskPriority = TaskPriority.normal
    is_primary: bool = False
    motivation: str | None = None
    start_date: datetime | None = None
    target_date: datetime | None = None
    weekly_target_minutes: int = 120
    status: ObjectiveStatus = ObjectiveStatus.active
    steps: list[dict[str, Any]] = []
    deliverables: list[str] = []
    next_action: str = ""
    success_criteria: list[str] = []
    progress_history: list[dict[str, Any]] = []
    skill_id: UUID | None = None
    learning_path_id: UUID | None = None
    course_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


def _to_path_record(row: LearningPathTable) -> LearningPathRecord:
    return LearningPathRecord(
        id=row.id,
        user_id=row.user_id,
        title=row.title,
        description=row.description,
        status=LearningStatus(row.status),
        goal=row.goal,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_module_record(row: LearningModuleTable) -> LearningModuleRecord:
    return LearningModuleRecord(
        id=row.id,
        user_id=row.user_id,
        path_id=row.path_id,
        title=row.title,
        description=row.description,
        position=row.position,
        status=LearningStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_lesson_record(row: LessonTable) -> LessonRecord:
    return LessonRecord(
        id=row.id,
        user_id=row.user_id,
        module_id=row.module_id,
        title=row.title,
        content=row.content,
        resource_url=row.resource_url,
        position=row.position,
        status=LearningStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_skill_record(row: SkillTable) -> SkillRecord:
    return SkillRecord(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        domain=row.domain,
        description=row.description,
        current_level=row.current_level,
        target_level=row.target_level,
        last_assessed_at=row.last_assessed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_evidence_record(row: SkillEvidenceTable) -> SkillEvidenceRecord:
    raw_verif = getattr(row, "verification_status", None) or "declared"
    return SkillEvidenceRecord(
        id=row.id,
        user_id=row.user_id,
        skill_id=row.skill_id,
        type=SkillEvidenceType(row.type),
        description=row.description,
        reference_url=row.reference_url,
        result=row.result,
        verification_status=EvidenceVerificationStatus(raw_verif),
        inspection_metadata=dict(getattr(row, "inspection_metadata", None) or {}),
        inspected_at=getattr(row, "inspected_at", None),
        is_locked=bool(getattr(row, "is_locked", False)),
        observed_at=row.observed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_assessment_record(row: SkillAssessmentTable) -> SkillAssessmentRecord:
    raw_eval_mode = getattr(row, "evaluation_mode", None) or "automated"
    return SkillAssessmentRecord(
        id=row.id,
        user_id=row.user_id,
        skill_id=row.skill_id,
        path_id=row.path_id,
        module_id=row.module_id,
        lesson_id=row.lesson_id,
        assessment_type=SkillAssessmentType(row.assessment_type),
        starting_level=row.starting_level,
        target_level=row.target_level,
        proposed_level=row.proposed_level,
        status=SkillAssessmentStatus(row.status),
        prompt_title=row.prompt_title,
        prompt_instructions=row.prompt_instructions,
        hints=list(row.hints or []),
        hints_revealed_count=row.hints_revealed_count,
        submission_text=row.submission_text,
        submission_code=row.submission_code,
        submission_reference_url=row.submission_reference_url,
        evidence_ids=list(row.evidence_ids or []),
        criteria=[dict(item) for item in (row.criteria or [])],
        rubric_version=getattr(row, "rubric_version", None) or "rubric-v2",
        evaluator_version=getattr(row, "evaluator_version", None) or "eval-v2",
        evaluation_mode=SkillEvaluationMode(raw_eval_mode),
        manual_review_required=bool(getattr(row, "manual_review_required", False)),
        rubric_snapshot=[dict(item) for item in (getattr(row, "rubric_snapshot", None) or [])],
        evidence_snapshot=[dict(item) for item in (getattr(row, "evidence_snapshot", None) or [])],
        reviewed_by=getattr(row, "reviewed_by", None),
        score=row.score,
        passed=row.passed,
        feedback=row.feedback,
        mastered_points=list(row.mastered_points or []),
        gaps_identified=list(row.gaps_identified or []),
        remediation_recommendation=row.remediation_recommendation,
        external_verification_warning=row.external_verification_warning,
        evaluator_type=SkillEvaluatorType(row.evaluator_type),
        evaluator_name=row.evaluator_name,
        decision_reason=row.decision_reason,
        applied_level_delta=row.applied_level_delta,
        submitted_at=row.submitted_at,
        evaluated_at=row.evaluated_at,
        validated_at=row.validated_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_project_record(row: ProjectTable) -> ProjectRecord:
    return ProjectRecord(
        id=row.id,
        user_id=row.user_id,
        category=getattr(row, "category", None) or "project",
        name=row.name,
        description=row.description,
        goal=row.goal,
        status=ProjectStatus(row.status),
        priority=TaskPriority(row.priority),
        motivation=getattr(row, "motivation", None),
        start_date=getattr(row, "start_date", None),
        weekly_target_minutes=int(getattr(row, "weekly_target_minutes", None) or 180),
        next_action=row.next_action,
        steps=list(getattr(row, "steps", None) or []),
        deliverables=list(row.deliverables) if row.deliverables is not None else None,
        success_criteria=list(getattr(row, "success_criteria", None) or []),
        progress_history=list(getattr(row, "progress_history", None) or []),
        target_date=row.target_date,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_personal_goal_record(row: PersonalGoalTable) -> PersonalGoalRecord:
    raw_cat = getattr(row, "category", None) or "learning_goal"
    try:
        cat_enum = ObjectiveCategory(raw_cat)
    except ValueError:
        cat_enum = ObjectiveCategory.learning_goal
    return PersonalGoalRecord(
        id=row.id,
        user_id=row.user_id,
        category=cat_enum,
        title=row.title,
        description=row.description,
        goal=row.goal,
        current_level=row.current_level,
        target_level=row.target_level,
        priority=TaskPriority(row.priority),
        is_primary=bool(getattr(row, "is_primary", False)),
        motivation=row.motivation,
        start_date=row.start_date,
        target_date=row.target_date,
        weekly_target_minutes=int(row.weekly_target_minutes or 0),
        status=ObjectiveStatus(row.status),
        steps=list(row.steps or []),
        deliverables=list(row.deliverables or []),
        next_action=row.next_action or "",
        success_criteria=list(row.success_criteria or []),
        progress_history=list(row.progress_history or []),
        skill_id=row.skill_id,
        learning_path_id=row.learning_path_id,
        course_id=row.course_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _get_owned_row(db: Session, table_cls: Any, row_id: UUID, user_id: UUID) -> Any | None:
    return db.scalar(
        select(table_cls).where(table_cls.id == row_id, table_cls.user_id == user_id)
    )


def _upsert_owned_row(
    db: Session,
    table_cls: type[TableT],
    row_id: UUID,
    user_id: UUID,
    data: dict[str, Any],
) -> TableT:
    row = _get_owned_row(db, table_cls, row_id, user_id)
    if row is None:
        row = table_cls(**data)
        db.add(row)
    else:
        for key, value in data.items():
            setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


def _delete_owned_row(db: Session, table_cls: Any, row_id: UUID, user_id: UUID) -> bool:
    row = _get_owned_row(db, table_cls, row_id, user_id)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


class SqlLearningRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_paths(self, user_id: UUID) -> list[LearningPathRecord]:
        rows = self._db.scalars(
            select(LearningPathTable).where(LearningPathTable.user_id == user_id)
        ).all()
        return [_to_path_record(row) for row in rows]

    def get_path(self, user_id: UUID, path_id: UUID) -> LearningPathRecord | None:
        row = _get_owned_row(self._db, LearningPathTable, path_id, user_id)
        return _to_path_record(row) if row else None

    def save_path(self, record: LearningPathRecord) -> LearningPathRecord:
        data = record.model_dump()
        data["status"] = record.status.value
        row = _upsert_owned_row(self._db, LearningPathTable, record.id, record.user_id, data)
        return _to_path_record(row)

    def delete_path(self, user_id: UUID, path_id: UUID) -> bool:
        modules = self.list_modules(user_id, path_id=path_id)
        module_ids = [module.id for module in modules]
        lesson_ids = [
            lesson.id
            for module_id in module_ids
            for lesson in self.list_lessons(user_id, module_id=module_id)
        ]
        self._db.execute(
            update(SkillAssessmentTable)
            .where(SkillAssessmentTable.user_id == user_id, SkillAssessmentTable.path_id == path_id)
            .values(path_id=None)
        )
        if module_ids:
            self._db.execute(
                update(SkillAssessmentTable)
                .where(
                    SkillAssessmentTable.user_id == user_id,
                    SkillAssessmentTable.module_id.in_(module_ids),
                )
                .values(module_id=None)
            )
        if lesson_ids:
            self._db.execute(
                update(SkillAssessmentTable)
                .where(
                    SkillAssessmentTable.user_id == user_id,
                    SkillAssessmentTable.lesson_id.in_(lesson_ids),
                )
                .values(lesson_id=None)
            )
            self._db.execute(
                delete(LessonTable).where(
                    LessonTable.user_id == user_id, LessonTable.id.in_(lesson_ids)
                )
            )
        if module_ids:
            self._db.execute(
                delete(LearningModuleTable).where(
                    LearningModuleTable.user_id == user_id,
                    LearningModuleTable.id.in_(module_ids),
                )
            )
        deleted = _delete_owned_row(self._db, LearningPathTable, path_id, user_id)
        return deleted

    def list_modules(
        self,
        user_id: UUID,
        *,
        path_id: UUID | None = None,
    ) -> list[LearningModuleRecord]:
        stmt = select(LearningModuleTable).where(LearningModuleTable.user_id == user_id)
        if path_id is not None:
            stmt = stmt.where(LearningModuleTable.path_id == path_id)
        rows = self._db.scalars(stmt).all()
        return [_to_module_record(row) for row in rows]

    def get_module(self, user_id: UUID, module_id: UUID) -> LearningModuleRecord | None:
        row = _get_owned_row(self._db, LearningModuleTable, module_id, user_id)
        return _to_module_record(row) if row else None

    def save_module(self, record: LearningModuleRecord) -> LearningModuleRecord:
        data = record.model_dump()
        data["status"] = record.status.value
        row = _upsert_owned_row(self._db, LearningModuleTable, record.id, record.user_id, data)
        return _to_module_record(row)

    def delete_module(self, user_id: UUID, module_id: UUID) -> bool:
        lesson_ids = [
            lesson.id for lesson in self.list_lessons(user_id, module_id=module_id)
        ]
        self._db.execute(
            update(SkillAssessmentTable)
            .where(SkillAssessmentTable.user_id == user_id, SkillAssessmentTable.module_id == module_id)
            .values(module_id=None)
        )
        if lesson_ids:
            self._db.execute(
                update(SkillAssessmentTable)
                .where(
                    SkillAssessmentTable.user_id == user_id,
                    SkillAssessmentTable.lesson_id.in_(lesson_ids),
                )
                .values(lesson_id=None)
            )
            self._db.execute(
                delete(LessonTable).where(
                    LessonTable.user_id == user_id, LessonTable.id.in_(lesson_ids)
                )
            )
        return _delete_owned_row(self._db, LearningModuleTable, module_id, user_id)

    def list_lessons(
        self,
        user_id: UUID,
        *,
        module_id: UUID | None = None,
    ) -> list[LessonRecord]:
        stmt = select(LessonTable).where(LessonTable.user_id == user_id)
        if module_id is not None:
            stmt = stmt.where(LessonTable.module_id == module_id)
        rows = self._db.scalars(stmt).all()
        return [_to_lesson_record(row) for row in rows]

    def get_lesson(self, user_id: UUID, lesson_id: UUID) -> LessonRecord | None:
        row = _get_owned_row(self._db, LessonTable, lesson_id, user_id)
        return _to_lesson_record(row) if row else None

    def save_lesson(self, record: LessonRecord) -> LessonRecord:
        data = record.model_dump()
        data["status"] = record.status.value
        row = _upsert_owned_row(self._db, LessonTable, record.id, record.user_id, data)
        return _to_lesson_record(row)

    def delete_lesson(self, user_id: UUID, lesson_id: UUID) -> bool:
        self._db.execute(
            update(SkillAssessmentTable)
            .where(SkillAssessmentTable.user_id == user_id, SkillAssessmentTable.lesson_id == lesson_id)
            .values(lesson_id=None)
        )
        return _delete_owned_row(self._db, LessonTable, lesson_id, user_id)

    def detach_modules(self, user_id: UUID, module_ids: list[UUID]) -> None:
        if not module_ids:
            return
        self._db.execute(
            update(TaskTable)
            .where(TaskTable.user_id == user_id, TaskTable.module_id.in_(module_ids))
            .values(module_id=None)
        )
        self._db.execute(
            update(StudySessionTable)
            .where(StudySessionTable.user_id == user_id, StudySessionTable.module_id.in_(module_ids))
            .values(module_id=None)
        )
        self._db.execute(
            update(SkillAssessmentTable)
            .where(SkillAssessmentTable.user_id == user_id, SkillAssessmentTable.module_id.in_(module_ids))
            .values(module_id=None)
        )
        self._db.commit()

    def detach_lessons(self, user_id: UUID, lesson_ids: list[UUID]) -> None:
        if not lesson_ids:
            return
        self._db.execute(
            update(StudySessionTable)
            .where(StudySessionTable.user_id == user_id, StudySessionTable.lesson_id.in_(lesson_ids))
            .values(lesson_id=None)
        )
        self._db.execute(
            update(SkillAssessmentTable)
            .where(SkillAssessmentTable.user_id == user_id, SkillAssessmentTable.lesson_id.in_(lesson_ids))
            .values(lesson_id=None)
        )
        self._db.commit()


class SqlSkillRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_skills(self, user_id: UUID) -> list[SkillRecord]:
        rows = self._db.scalars(
            select(SkillTable).where(SkillTable.user_id == user_id)
        ).all()
        return [_to_skill_record(row) for row in rows]

    def get_skill(self, user_id: UUID, skill_id: UUID) -> SkillRecord | None:
        row = _get_owned_row(self._db, SkillTable, skill_id, user_id)
        return _to_skill_record(row) if row else None

    def save_skill(self, record: SkillRecord) -> SkillRecord:
        row = _upsert_owned_row(
            self._db, SkillTable, record.id, record.user_id, record.model_dump()
        )
        return _to_skill_record(row)

    def delete_skill(self, user_id: UUID, skill_id: UUID) -> bool:
        row = _get_owned_row(self._db, SkillTable, skill_id, user_id)
        if row is None:
            return False
        self._db.execute(
            delete(SkillAssessmentTable).where(
                SkillAssessmentTable.user_id == user_id,
                SkillAssessmentTable.skill_id == skill_id,
            )
        )
        self._db.execute(
            delete(SkillEvidenceTable).where(
                SkillEvidenceTable.user_id == user_id,
                SkillEvidenceTable.skill_id == skill_id,
            )
        )
        self._db.execute(
            update(StudySessionTable)
            .where(StudySessionTable.user_id == user_id, StudySessionTable.skill_id == skill_id)
            .values(skill_id=None)
        )
        self._db.delete(row)
        self._db.commit()
        return True

    def list_evidence(
        self,
        user_id: UUID,
        *,
        skill_id: UUID | None = None,
    ) -> list[SkillEvidenceRecord]:
        stmt = select(SkillEvidenceTable).where(SkillEvidenceTable.user_id == user_id)
        if skill_id is not None:
            stmt = stmt.where(SkillEvidenceTable.skill_id == skill_id)
        rows = self._db.scalars(stmt).all()
        return [_to_evidence_record(row) for row in rows]

    def get_evidence(self, user_id: UUID, evidence_id: UUID) -> SkillEvidenceRecord | None:
        row = _get_owned_row(self._db, SkillEvidenceTable, evidence_id, user_id)
        return _to_evidence_record(row) if row else None

    def save_evidence(self, record: SkillEvidenceRecord) -> SkillEvidenceRecord:
        data = record.model_dump()
        data["type"] = record.type.value
        data["verification_status"] = record.verification_status.value
        row = _upsert_owned_row(self._db, SkillEvidenceTable, record.id, record.user_id, data)
        return _to_evidence_record(row)

    def delete_evidence(self, user_id: UUID, evidence_id: UUID) -> bool:
        return _delete_owned_row(self._db, SkillEvidenceTable, evidence_id, user_id)

    def list_assessments(
        self,
        user_id: UUID,
        *,
        skill_id: UUID | None = None,
        status: SkillAssessmentStatus | None = None,
        path_id: UUID | None = None,
        module_id: UUID | None = None,
        lesson_id: UUID | None = None,
    ) -> list[SkillAssessmentRecord]:
        stmt = select(SkillAssessmentTable).where(SkillAssessmentTable.user_id == user_id)
        if skill_id is not None:
            stmt = stmt.where(SkillAssessmentTable.skill_id == skill_id)
        if status is not None:
            stmt = stmt.where(SkillAssessmentTable.status == status.value)
        if path_id is not None:
            stmt = stmt.where(SkillAssessmentTable.path_id == path_id)
        if module_id is not None:
            stmt = stmt.where(SkillAssessmentTable.module_id == module_id)
        if lesson_id is not None:
            stmt = stmt.where(SkillAssessmentTable.lesson_id == lesson_id)
        rows = self._db.scalars(stmt).all()
        return [_to_assessment_record(row) for row in rows]

    def get_assessment(self, user_id: UUID, assessment_id: UUID) -> SkillAssessmentRecord | None:
        row = _get_owned_row(self._db, SkillAssessmentTable, assessment_id, user_id)
        return _to_assessment_record(row) if row else None

    def save_assessment(self, record: SkillAssessmentRecord) -> SkillAssessmentRecord:
        data = record.model_dump()
        data["assessment_type"] = record.assessment_type.value
        data["status"] = record.status.value
        data["evaluator_type"] = record.evaluator_type.value
        data["evaluation_mode"] = record.evaluation_mode.value
        row = _upsert_owned_row(self._db, SkillAssessmentTable, record.id, record.user_id, data)
        return _to_assessment_record(row)

    def approve_assessment_and_update_skill(
        self,
        assessment_record: SkillAssessmentRecord,
        skill_record: SkillRecord,
        consumed_evidence_ids: list[UUID] | None = None,
    ) -> tuple[SkillAssessmentRecord, SkillRecord]:
        """Valide l'évaluation de manière conditionnellement atomique et verrouille les preuves associées."""
        claimed = self._db.execute(
            update(SkillAssessmentTable)
            .where(
                SkillAssessmentTable.id == assessment_record.id,
                SkillAssessmentTable.user_id == assessment_record.user_id,
                SkillAssessmentTable.status == SkillAssessmentStatus.evaluated.value,
                SkillAssessmentTable.manual_review_required.is_(False),
                SkillAssessmentTable.passed.is_(True),
            )
            .values(
                status=SkillAssessmentStatus.approved.value,
                decision_reason=assessment_record.decision_reason,
                applied_level_delta=assessment_record.applied_level_delta,
                validated_at=assessment_record.validated_at,
                updated_at=assessment_record.updated_at,
            )
        )
        if int(claimed.rowcount or 0) != 1:
            self._db.rollback()
            raise AppError(
                409,
                "ASSESSMENT_ALREADY_APPROVED",
                "Cette évaluation a déjà été validée ou n'est plus éligible à la validation.",
            )

        skill_row = _get_owned_row(
            self._db, SkillTable, skill_record.id, skill_record.user_id
        )
        if skill_row is None:
            self._db.rollback()
            raise ValueError("Impossible de synchroniser une compétence inexistante.")

        skill_row.current_level = skill_record.current_level
        skill_row.last_assessed_at = skill_record.last_assessed_at
        skill_row.updated_at = skill_record.updated_at

        if consumed_evidence_ids:
            self._db.execute(
                update(SkillEvidenceTable)
                .where(
                    SkillEvidenceTable.user_id == assessment_record.user_id,
                    SkillEvidenceTable.skill_id == assessment_record.skill_id,
                    SkillEvidenceTable.id.in_(consumed_evidence_ids),
                )
                .values(
                    is_locked=True,
                    verification_status=EvidenceVerificationStatus.approved.value,
                    updated_at=assessment_record.updated_at,
                )
            )

        self._db.commit()
        assessment_row = _get_owned_row(
            self._db, SkillAssessmentTable, assessment_record.id, assessment_record.user_id
        )
        self._db.refresh(skill_row)
        return _to_assessment_record(assessment_row), _to_skill_record(skill_row)


class SqlProjectRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_projects(self, user_id: UUID) -> list[ProjectRecord]:
        rows = self._db.scalars(
            select(ProjectTable).where(ProjectTable.user_id == user_id)
        ).all()
        return [_to_project_record(row) for row in rows]

    def get(self, user_id: UUID, project_id: UUID) -> ProjectRecord | None:
        row = _get_owned_row(self._db, ProjectTable, project_id, user_id)
        return _to_project_record(row) if row else None

    def save(self, record: ProjectRecord) -> ProjectRecord:
        data = record.model_dump()
        data["status"] = record.status.value
        data["priority"] = record.priority.value
        row = _upsert_owned_row(self._db, ProjectTable, record.id, record.user_id, data)
        return _to_project_record(row)

    def delete(self, user_id: UUID, project_id: UUID) -> bool:
        deleted = _delete_owned_row(self._db, ProjectTable, project_id, user_id)
        if deleted:
            self._db.execute(
                update(TaskTable)
                .where(TaskTable.user_id == user_id, TaskTable.project_id == project_id)
                .values(project_id=None)
            )
            self._db.execute(
                update(StudySessionTable)
                .where(StudySessionTable.user_id == user_id, StudySessionTable.project_id == project_id)
                .values(project_id=None)
            )
            self._db.commit()
        return deleted


class SqlPersonalGoalRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_goals(self, user_id: UUID) -> list[PersonalGoalRecord]:
        rows = self._db.scalars(
            select(PersonalGoalTable).where(PersonalGoalTable.user_id == user_id)
        ).all()
        return [_to_personal_goal_record(row) for row in rows]

    def get(self, user_id: UUID, goal_id: UUID) -> PersonalGoalRecord | None:
        row = _get_owned_row(self._db, PersonalGoalTable, goal_id, user_id)
        return _to_personal_goal_record(row) if row else None

    def save(self, record: PersonalGoalRecord) -> PersonalGoalRecord:
        data = record.model_dump()
        data["category"] = record.category.value
        data["status"] = record.status.value
        data["priority"] = record.priority.value
        row = _upsert_owned_row(self._db, PersonalGoalTable, record.id, record.user_id, data)
        return _to_personal_goal_record(row)

    def delete(self, user_id: UUID, goal_id: UUID) -> bool:
        deleted = _delete_owned_row(self._db, PersonalGoalTable, goal_id, user_id)
        if deleted:
            self._db.execute(
                update(StudySessionTable)
                .where(StudySessionTable.user_id == user_id, StudySessionTable.goal_id == goal_id)
                .values(goal_id=None)
            )
            self._db.commit()
        return deleted
