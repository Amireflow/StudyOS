from datetime import datetime
from threading import RLock
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field
from app.schemas.common import (
    ScheduleEventType,
    SessionStatus,
    TaskPriority,
    TaskSource,
    TaskStatus,
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
    created_at: datetime
    updated_at: datetime


class SessionRecord(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    category: str
    status: SessionStatus
    started_at: datetime
    ended_at: datetime | None = None
    result: str | None = None
    task_id: UUID | None = None
    project_id: UUID | None = None
    module_id: UUID | None = None
    lesson_id: UUID | None = None
    skill_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class InMemoryStore:
    """Conteneur thread-safe isolé par instance d'application pour le Lot 4."""

    def __init__(self) -> None:
        self.lock = RLock()
        self.profiles: dict[UUID, ProfileRecord] = {}
        self.tasks: dict[UUID, TaskRecord] = {}
        self.schedule_events: dict[UUID, ScheduleEventRecord] = {}
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
