from datetime import datetime
from uuid import UUID
from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session
from app.models.tables import (
    ProfileTable,
    ScheduleEventTable,
    StudySessionTable,
    TaskTable,
    TimetableImportTable,
)
from app.repositories.memory import (
    ProfileRecord,
    ScheduleEventRecord,
    SessionRecord,
    TaskRecord,
    TimetableImportRecord,
)
from app.schemas.common import (
    ScheduleEventSource,
    ScheduleEventType,
    SessionStatus,
    TaskPriority,
    TaskSource,
    TaskStatus,
    TimetableFileFormat,
    TimetableImportStatus,
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
    raw_source = getattr(row, "source", None) or "manual"
    return ScheduleEventRecord(
        id=row.id,
        user_id=row.user_id,
        title=row.title,
        type=ScheduleEventType(row.type),
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        notes=row.notes,
        source=ScheduleEventSource(raw_source),
        import_id=getattr(row, "import_id", None),
        session_subtype=getattr(row, "session_subtype", None),
        teacher=getattr(row, "teacher", None),
        room=getattr(row, "room", None),
        group_name=getattr(row, "group_name", None),
        goal_id=getattr(row, "goal_id", None),
        course_id=getattr(row, "course_id", None),
        project_id=getattr(row, "project_id", None),
        task_id=getattr(row, "task_id", None),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_timetable_import_record(row: TimetableImportTable) -> TimetableImportRecord:
    return TimetableImportRecord(
        id=row.id,
        user_id=row.user_id,
        filename=row.filename,
        file_format=TimetableFileFormat(row.file_format),
        mime_type=row.mime_type,
        file_size_bytes=row.file_size_bytes,
        file_sha256=row.file_sha256,
        source_preview_text=row.source_preview_text,
        source_deleted=bool(row.source_deleted),
        status=TimetableImportStatus(row.status),
        valid_from=row.valid_from,
        valid_until=row.valid_until,
        extracted_courses=list(row.extracted_courses or []),
        anomalies=list(row.anomalies or []),
        warnings=list(row.warnings or []),
        created_events_count=row.created_events_count,
        skipped_duplicates_count=row.skipped_duplicates_count,
        replaced_events_count=row.replaced_events_count,
        replaced_snapshot=getattr(row, "replaced_snapshot", None),
        created_at=row.created_at,
        updated_at=row.updated_at,
        validated_at=row.validated_at,
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
        planned_activity=getattr(row, "planned_activity", None),
        actual_activity=getattr(row, "actual_activity", None),
        outcome_status=getattr(row, "outcome_status", None),
        deliverable_summary=getattr(row, "deliverable_summary", None),
        blockers=getattr(row, "blockers", None),
        next_step=getattr(row, "next_step", None),
        task_id=row.task_id,
        project_id=row.project_id,
        goal_id=getattr(row, "goal_id", None),
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
        data["source"] = record.source.value
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
            data["source"] = record.source.value
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

    def delete_imported_events(
        self,
        user_id: UUID,
        *,
        range_start: datetime | None = None,
        range_end: datetime | None = None,
    ) -> int:
        stmt = select(ScheduleEventTable).where(
            ScheduleEventTable.user_id == user_id,
            or_(
                ScheduleEventTable.source == ScheduleEventSource.timetable_import.value,
                ScheduleEventTable.import_id.is_not(None),
            ),
        )
        if range_start is not None:
            stmt = stmt.where(ScheduleEventTable.starts_at >= range_start)
        if range_end is not None:
            stmt = stmt.where(ScheduleEventTable.starts_at <= range_end)
        rows = self._db.scalars(stmt).all()
        for row in rows:
            self._db.delete(row)
        self._db.commit()
        return len(rows)

    def list_imports_by_user(self, user_id: UUID) -> list[TimetableImportRecord]:
        rows = self._db.scalars(
            select(TimetableImportTable)
            .where(TimetableImportTable.user_id == user_id)
            .order_by(TimetableImportTable.created_at.desc())
        ).all()
        return [_to_timetable_import_record(row) for row in rows]

    def get_import(self, user_id: UUID, import_id: UUID) -> TimetableImportRecord | None:
        row = self._db.scalar(
            select(TimetableImportTable).where(
                TimetableImportTable.id == import_id,
                TimetableImportTable.user_id == user_id,
            )
        )
        return _to_timetable_import_record(row) if row else None

    def save_import(self, record: TimetableImportRecord) -> TimetableImportRecord:
        row = self._db.scalar(
            select(TimetableImportTable).where(
                TimetableImportTable.id == record.id,
                TimetableImportTable.user_id == record.user_id,
            )
        )
        data = record.model_dump()
        data["file_format"] = record.file_format.value
        data["status"] = record.status.value
        if row is None:
            row = TimetableImportTable(**data)
            self._db.add(row)
        else:
            for key, value in data.items():
                setattr(row, key, value)
        self._db.commit()
        self._db.refresh(row)
        return _to_timetable_import_record(row)


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
