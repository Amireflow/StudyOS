from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app.models.tables import (
    ProfileTable,
    ScheduleEventTable,
    StudySessionTable,
    TaskTable,
)
from app.repositories.memory import (
    ProfileRecord,
    ScheduleEventRecord,
    SessionRecord,
    TaskRecord,
)
from app.schemas.common import (
    ScheduleEventType,
    SessionStatus,
    TaskPriority,
    TaskSource,
    TaskStatus,
)


def _to_profile_record(row: ProfileTable) -> ProfileRecord:
    return ProfileRecord(
        id=row.id,
        display_name=row.display_name,
        timezone=row.timezone,
        active_priority_title=row.active_priority_title,
        active_priority_task_id=row.active_priority_task_id,
        active_priority_project_id=row.active_priority_project_id,
        preferences=dict(row.preferences or {}),
        ai_instructions=row.ai_instructions,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_task_record(row: TaskTable) -> TaskRecord:
    return TaskRecord(
        id=row.id,
        user_id=row.user_id,
        title=row.title,
        description=row.description,
        status=TaskStatus(row.status),
        priority=TaskPriority(row.priority),
        due_at=row.due_at,
        completed_at=row.completed_at,
        source=TaskSource(row.source),
        proposal_id=row.proposal_id,
        project_id=row.project_id,
        module_id=row.module_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_schedule_record(row: ScheduleEventTable) -> ScheduleEventRecord:
    return ScheduleEventRecord(
        id=row.id,
        user_id=row.user_id,
        title=row.title,
        type=ScheduleEventType(row.type),
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_session_record(row: StudySessionTable) -> SessionRecord:
    return SessionRecord(
        id=row.id,
        user_id=row.user_id,
        title=row.title,
        category=row.category,
        status=SessionStatus(row.status),
        started_at=row.started_at,
        ended_at=row.ended_at,
        result=row.result,
        task_id=row.task_id,
        project_id=row.project_id,
        module_id=row.module_id,
        lesson_id=row.lesson_id,
        skill_id=row.skill_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlProfileRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, user_id: UUID) -> ProfileRecord | None:
        row = self._db.scalar(select(ProfileTable).where(ProfileTable.id == user_id))
        return _to_profile_record(row) if row else None

    def save(self, record: ProfileRecord) -> ProfileRecord:
        row = self._db.scalar(select(ProfileTable).where(ProfileTable.id == record.id))
        data = record.model_dump()
        if row is None:
            row = ProfileTable(**data)
            self._db.add(row)
        else:
            for key, value in data.items():
                setattr(row, key, value)
        self._db.commit()
        self._db.refresh(row)
        return _to_profile_record(row)


class SqlTaskRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_by_user(self, user_id: UUID) -> list[TaskRecord]:
        rows = self._db.scalars(select(TaskTable).where(TaskTable.user_id == user_id)).all()
        return [_to_task_record(row) for row in rows]

    def get(self, user_id: UUID, task_id: UUID) -> TaskRecord | None:
        row = self._db.scalar(
            select(TaskTable).where(TaskTable.id == task_id, TaskTable.user_id == user_id)
        )
        return _to_task_record(row) if row else None

    def save(self, record: TaskRecord) -> TaskRecord:
        row = self._db.scalar(
            select(TaskTable).where(TaskTable.id == record.id, TaskTable.user_id == record.user_id)
        )
        data = record.model_dump()
        data["status"] = record.status.value
        data["priority"] = record.priority.value
        data["source"] = record.source.value
        if row is None:
            row = TaskTable(**data)
            self._db.add(row)
        else:
            for key, value in data.items():
                setattr(row, key, value)
        self._db.commit()
        self._db.refresh(row)
        return _to_task_record(row)

    def delete(self, user_id: UUID, task_id: UUID) -> bool:
        row = self._db.scalar(
            select(TaskTable).where(TaskTable.id == task_id, TaskTable.user_id == user_id)
        )
        if row is None:
            return False
        self._db.delete(row)
        self._db.commit()
        return True


class SqlScheduleRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_by_user(self, user_id: UUID) -> list[ScheduleEventRecord]:
        rows = self._db.scalars(
            select(ScheduleEventTable).where(ScheduleEventTable.user_id == user_id)
        ).all()
        return [_to_schedule_record(row) for row in rows]

    def get(self, user_id: UUID, event_id: UUID) -> ScheduleEventRecord | None:
        row = self._db.scalar(
            select(ScheduleEventTable).where(
                ScheduleEventTable.id == event_id,
                ScheduleEventTable.user_id == user_id,
            )
        )
        return _to_schedule_record(row) if row else None

    def save(self, record: ScheduleEventRecord) -> ScheduleEventRecord:
        row = self._db.scalar(
            select(ScheduleEventTable).where(
                ScheduleEventTable.id == record.id,
                ScheduleEventTable.user_id == record.user_id,
            )
        )
        data = record.model_dump()
        data["type"] = record.type.value
        if row is None:
            row = ScheduleEventTable(**data)
            self._db.add(row)
        else:
            for key, value in data.items():
                setattr(row, key, value)
        self._db.commit()
        self._db.refresh(row)
        return _to_schedule_record(row)

    def save_many(self, records: list[ScheduleEventRecord]) -> list[ScheduleEventRecord]:
        rows: list[ScheduleEventTable] = []
        for record in records:
            data = record.model_dump()
            data["type"] = record.type.value
            row = ScheduleEventTable(**data)
            self._db.add(row)
            rows.append(row)
        self._db.commit()
        for row in rows:
            self._db.refresh(row)
        return [_to_schedule_record(row) for row in rows]

    def delete(self, user_id: UUID, event_id: UUID) -> bool:
        row = self._db.scalar(
            select(ScheduleEventTable).where(
                ScheduleEventTable.id == event_id,
                ScheduleEventTable.user_id == user_id,
            )
        )
        if row is None:
            return False
        self._db.delete(row)
        self._db.commit()
        return True


class SqlSessionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_by_user(self, user_id: UUID) -> list[SessionRecord]:
        rows = self._db.scalars(
            select(StudySessionTable).where(StudySessionTable.user_id == user_id)
        ).all()
        return [_to_session_record(row) for row in rows]

    def get(self, user_id: UUID, session_id: UUID) -> SessionRecord | None:
        row = self._db.scalar(
            select(StudySessionTable).where(
                StudySessionTable.id == session_id,
                StudySessionTable.user_id == user_id,
            )
        )
        return _to_session_record(row) if row else None

    def save(self, record: SessionRecord) -> SessionRecord:
        row = self._db.scalar(
            select(StudySessionTable).where(
                StudySessionTable.id == record.id,
                StudySessionTable.user_id == record.user_id,
            )
        )
        data = record.model_dump()
        data["status"] = record.status.value
        if row is None:
            row = StudySessionTable(**data)
            self._db.add(row)
        else:
            for key, value in data.items():
                setattr(row, key, value)
        self._db.commit()
        self._db.refresh(row)
        return _to_session_record(row)

    def delete(self, user_id: UUID, session_id: UUID) -> bool:
        row = self._db.scalar(
            select(StudySessionTable).where(
                StudySessionTable.id == session_id,
                StudySessionTable.user_id == user_id,
            )
        )
        if row is None:
            return False
        self._db.delete(row)
        self._db.commit()
        return True

    def detach_task(self, user_id: UUID, task_id: UUID) -> None:
        self._db.execute(
            update(StudySessionTable)
            .where(
                StudySessionTable.user_id == user_id,
                StudySessionTable.task_id == task_id,
            )
            .values(task_id=None)
        )
        self._db.commit()
