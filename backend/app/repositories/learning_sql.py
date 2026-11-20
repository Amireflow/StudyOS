from datetime import datetime
from typing import Any, TypeVar
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app.models.tables import (
    LearningModuleTable,
    LearningPathTable,
    LessonTable,
    ProjectTable,
    SkillEvidenceTable,
    SkillTable,
    StudySessionTable,
    TaskTable,
)
from app.schemas.common import (
    LearningStatus,
    ProjectStatus,
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
    observed_at: datetime
    created_at: datetime
    updated_at: datetime


class ProjectRecord(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: str | None = None
    goal: str
    status: ProjectStatus = ProjectStatus.planned
    priority: TaskPriority = TaskPriority.normal
    next_action: str = ""
    deliverables: list[str] | None = None
    target_date: datetime | None = None
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
    return SkillEvidenceRecord(
        id=row.id,
        user_id=row.user_id,
        skill_id=row.skill_id,
        type=SkillEvidenceType(row.type),
        description=row.description,
        reference_url=row.reference_url,
        result=row.result,
        observed_at=row.observed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_project_record(row: ProjectTable) -> ProjectRecord:
    return ProjectRecord(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        description=row.description,
        goal=row.goal,
        status=ProjectStatus(row.status),
        priority=TaskPriority(row.priority),
        next_action=row.next_action,
        deliverables=list(row.deliverables) if row.deliverables is not None else None,
        target_date=row.target_date,
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
        return _delete_owned_row(self._db, LearningPathTable, path_id, user_id)

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
        self._db.commit()

    def detach_lessons(self, user_id: UUID, lesson_ids: list[UUID]) -> None:
        if not lesson_ids:
            return
        self._db.execute(
            update(StudySessionTable)
            .where(StudySessionTable.user_id == user_id, StudySessionTable.lesson_id.in_(lesson_ids))
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
        deleted = _delete_owned_row(self._db, SkillTable, skill_id, user_id)
        if deleted:
            self._db.execute(
                update(StudySessionTable)
                .where(StudySessionTable.user_id == user_id, StudySessionTable.skill_id == skill_id)
                .values(skill_id=None)
            )
            self._db.commit()
        return deleted

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
        row = _upsert_owned_row(self._db, SkillEvidenceTable, record.id, record.user_id, data)
        return _to_evidence_record(row)

    def delete_evidence(self, user_id: UUID, evidence_id: UUID) -> bool:
        return _delete_owned_row(self._db, SkillEvidenceTable, evidence_id, user_id)


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
