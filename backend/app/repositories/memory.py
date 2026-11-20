from datetime import datetime
from threading import RLock
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field
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


class ProfileRecord(BaseModel):
    id: UUID
    display_name: str
    timezone: str
    active_priority_title: str | None = None
    active_priority_task_id: UUID | None = None
    active_priority_project_id: UUID | None = None
    preferences: dict[str, Any] = Field(default_factory=dict)
    ai_instructions: str | None = None
    created_at: datetime
    updated_at: datetime


class TaskRecord(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    description: str | None = None
    status: TaskStatus
    priority: TaskPriority
    due_at: datetime | None = None
    completed_at: datetime | None = None
    source: TaskSource = TaskSource.manual
    proposal_id: UUID | None = None
    project_id: UUID | None = None
    module_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class ScheduleEventRecord(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    type: ScheduleEventType
    starts_at: datetime
    ends_at: datetime
    notes: str | None = None
    source: ScheduleEventSource = ScheduleEventSource.manual
    import_id: UUID | None = None
    session_subtype: str | None = None
    teacher: str | None = None
    room: str | None = None
    group_name: str | None = None
    goal_id: UUID | None = None
    course_id: UUID | None = None
    project_id: UUID | None = None
    task_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class TimetableImportRecord(BaseModel):
    id: UUID
    user_id: UUID
    filename: str
    file_format: TimetableFileFormat
    mime_type: str
    file_size_bytes: int
    file_sha256: str
    source_preview_text: str | None = None
    source_deleted: bool = False
    status: TimetableImportStatus = TimetableImportStatus.pending_review
    valid_from: str | None = None
    valid_until: str | None = None
    extracted_courses: list[dict[str, Any]] = Field(default_factory=list)
    anomalies: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_events_count: int = 0
    skipped_duplicates_count: int = 0
    replaced_events_count: int = 0
    replaced_snapshot: list[dict[str, Any]] | None = None
    created_at: datetime
    updated_at: datetime
    validated_at: datetime | None = None


class SessionRecord(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    category: str
    status: SessionStatus
    started_at: datetime
    ended_at: datetime | None = None
    result: str | None = None
    planned_activity: str | None = None
    actual_activity: str | None = None
    outcome_status: str | None = None
    deliverable_summary: str | None = None
    blockers: str | None = None
    next_step: str | None = None
    task_id: UUID | None = None
    project_id: UUID | None = None
    goal_id: UUID | None = None
    module_id: UUID | None = None
    lesson_id: UUID | None = None
    skill_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class InMemoryStore:
    """Conteneur thread-safe isolé par instance d'application pour le Lot 4."""

    def __init__(self) -> None:
        self.lock = RLock()
        self.users: dict[UUID, Any] = {}
        self.profiles: dict[UUID, ProfileRecord] = {}
        self.ai_provider_configs: dict[UUID, Any] = {}
        self.auth_refresh_sessions: dict[UUID, Any] = {}
        self.auth_login_attempts: list[Any] = []
        self.auth_token_revocations: dict[UUID, datetime] = {}
        self.tasks: dict[UUID, TaskRecord] = {}
        self.schedule_events: dict[UUID, ScheduleEventRecord] = {}
        self.timetable_imports: dict[UUID, TimetableImportRecord] = {}
        self.sessions: dict[UUID, SessionRecord] = {}


class ProfileRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def get(self, user_id: UUID) -> ProfileRecord | None:
        with self._store.lock:
            record = self._store.profiles.get(user_id)
            return record.model_copy(deep=True) if record else None

    def save(self, record: ProfileRecord) -> ProfileRecord:
        with self._store.lock:
            stored = record.model_copy(deep=True)
            self._store.profiles[record.id] = stored
            return stored.model_copy(deep=True)


class TaskRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def list_by_user(self, user_id: UUID) -> list[TaskRecord]:
        with self._store.lock:
            return [
                record.model_copy(deep=True)
                for record in self._store.tasks.values()
                if record.user_id == user_id
            ]

    def get(self, user_id: UUID, task_id: UUID) -> TaskRecord | None:
        with self._store.lock:
            record = self._store.tasks.get(task_id)
            if record is None or record.user_id != user_id:
                return None
            return record.model_copy(deep=True)

    def save(self, record: TaskRecord) -> TaskRecord:
        with self._store.lock:
            stored = record.model_copy(deep=True)
            self._store.tasks[record.id] = stored
            return stored.model_copy(deep=True)

    def delete(self, user_id: UUID, task_id: UUID) -> bool:
        with self._store.lock:
            record = self._store.tasks.get(task_id)
            if record is None or record.user_id != user_id:
                return False
            del self._store.tasks[task_id]
            return True


class ScheduleRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def list_by_user(self, user_id: UUID) -> list[ScheduleEventRecord]:
        with self._store.lock:
            return [
                record.model_copy(deep=True)
                for record in self._store.schedule_events.values()
                if record.user_id == user_id
            ]

    def get(self, user_id: UUID, event_id: UUID) -> ScheduleEventRecord | None:
        with self._store.lock:
            record = self._store.schedule_events.get(event_id)
            if record is None or record.user_id != user_id:
                return None
            return record.model_copy(deep=True)

    def save(self, record: ScheduleEventRecord) -> ScheduleEventRecord:
        with self._store.lock:
            stored = record.model_copy(deep=True)
            self._store.schedule_events[record.id] = stored
            return stored.model_copy(deep=True)

    def save_many(self, records: list[ScheduleEventRecord]) -> list[ScheduleEventRecord]:
        with self._store.lock:
            saved: list[ScheduleEventRecord] = []
            for record in records:
                stored = record.model_copy(deep=True)
                self._store.schedule_events[record.id] = stored
                saved.append(stored.model_copy(deep=True))
            return saved

    def delete(self, user_id: UUID, event_id: UUID) -> bool:
        with self._store.lock:
            record = self._store.schedule_events.get(event_id)
            if record is None or record.user_id != user_id:
                return False
            del self._store.schedule_events[event_id]
            return True

    def delete_imported_events(
        self,
        user_id: UUID,
        *,
        range_start: datetime | None = None,
        range_end: datetime | None = None,
    ) -> int:
        with self._store.lock:
            to_delete: list[UUID] = []
            for eid, rec in self._store.schedule_events.items():
                if rec.user_id != user_id:
                    continue
                if rec.source != ScheduleEventSource.timetable_import and rec.import_id is None:
                    continue
                if range_start is not None and rec.starts_at < range_start:
                    continue
                if range_end is not None and rec.starts_at > range_end:
                    continue
                to_delete.append(eid)
            for eid in to_delete:
                del self._store.schedule_events[eid]
            return len(to_delete)

    def list_imports_by_user(self, user_id: UUID) -> list[TimetableImportRecord]:
        with self._store.lock:
            items = [
                record.model_copy(deep=True)
                for record in self._store.timetable_imports.values()
                if record.user_id == user_id
            ]
            items.sort(key=lambda item: item.created_at, reverse=True)
            return items

    def get_import(self, user_id: UUID, import_id: UUID) -> TimetableImportRecord | None:
        with self._store.lock:
            record = self._store.timetable_imports.get(import_id)
            if record is None or record.user_id != user_id:
                return None
            return record.model_copy(deep=True)

    def save_import(self, record: TimetableImportRecord) -> TimetableImportRecord:
        with self._store.lock:
            stored = record.model_copy(deep=True)
            self._store.timetable_imports[record.id] = stored
            return stored.model_copy(deep=True)


class SessionRepository:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def list_by_user(self, user_id: UUID) -> list[SessionRecord]:
        with self._store.lock:
            return [
                record.model_copy(deep=True)
                for record in self._store.sessions.values()
                if record.user_id == user_id
            ]

    def get(self, user_id: UUID, session_id: UUID) -> SessionRecord | None:
        with self._store.lock:
            record = self._store.sessions.get(session_id)
            if record is None or record.user_id != user_id:
                return None
            return record.model_copy(deep=True)

    def save(self, record: SessionRecord) -> SessionRecord:
        with self._store.lock:
            stored = record.model_copy(deep=True)
            self._store.sessions[record.id] = stored
            return stored.model_copy(deep=True)

    def delete(self, user_id: UUID, session_id: UUID) -> bool:
        with self._store.lock:
            record = self._store.sessions.get(session_id)
            if record is None or record.user_id != user_id:
                return False
            del self._store.sessions[session_id]
            return True

    def detach_task(self, user_id: UUID, task_id: UUID) -> None:
        with self._store.lock:
            for session_id, session in list(self._store.sessions.items()):
                if session.user_id == user_id and session.task_id == task_id:
                    self._store.sessions[session_id] = session.model_copy(
                        update={"task_id": None}
                    )
