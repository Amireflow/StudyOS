from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4
from app.core.errors import AppError
from app.repositories.memory import SessionRecord, SessionRepository, TaskRepository
from app.schemas.common import SessionStatus
from app.schemas.sessions import (
    SessionCreate,
    SessionFinish,
    SessionResponse,
    SessionSummary,
    SessionUpdate,
)


def compute_session_duration_minutes(
    record: SessionRecord,
    now_utc: datetime | None = None,
) -> int:
    if record.ended_at is not None:
        return max(0, round((record.ended_at - record.started_at).total_seconds() / 60))
    if record.status == SessionStatus.in_progress:
        end_ref = now_utc or datetime.now(timezone.utc)
        return max(0, round((end_ref - record.started_at).total_seconds() / 60))
    return 0


def compute_session_summary(sessions: list[SessionRecord]) -> SessionSummary:
    """Les séances annulées ou en cours ne comptent jamais dans les totaux achevés (SESSION-03)."""
    completed_count = 0
    total_completed_minutes = 0
    in_progress_count = 0
    cancelled_count = 0

    for session in sessions:
        if session.status == SessionStatus.completed and session.ended_at is not None:
            completed_count += 1
            total_completed_minutes += compute_session_duration_minutes(session)
        elif session.status == SessionStatus.in_progress:
            in_progress_count += 1
        elif session.status == SessionStatus.cancelled:
            cancelled_count += 1

    return SessionSummary(
        completed_count=completed_count,
        total_completed_minutes=total_completed_minutes,
        in_progress_count=in_progress_count,
        cancelled_count=cancelled_count,
    )


def to_session_response(record: SessionRecord) -> SessionResponse:
    return SessionResponse(
        **record.model_dump(),
        duration_minutes=compute_session_duration_minutes(record),
    )


class SessionService:
    def __init__(
        self,
        session_repo: SessionRepository,
        task_repo: TaskRepository,
        project_repo: Any | None = None,
        learning_repo: Any | None = None,
        skill_repo: Any | None = None,
    ) -> None:
        self._session_repo = session_repo
        self._task_repo = task_repo
        self._project_repo = project_repo
        self._learning_repo = learning_repo
        self._skill_repo = skill_repo

    def _validate_task_ownership(self, user_id: UUID, task_id: UUID | None) -> None:
        if task_id is not None and self._task_repo.get(user_id, task_id) is None:
            raise AppError(404, "NOT_FOUND", "Tâche associée introuvable.")

    def _validate_palier2_links(
        self,
        user_id: UUID,
        *,
        project_id: UUID | None = None,
        module_id: UUID | None = None,
        lesson_id: UUID | None = None,
        skill_id: UUID | None = None,
    ) -> None:
        if (
            project_id is not None
            and self._project_repo is not None
            and self._project_repo.get(user_id, project_id) is None
        ):
            raise AppError(404, "NOT_FOUND", "Projet associé introuvable.")
        if (
            module_id is not None
            and self._learning_repo is not None
            and self._learning_repo.get_module(user_id, module_id) is None
        ):
            raise AppError(404, "NOT_FOUND", "Module associé introuvable.")
        if (
            lesson_id is not None
            and self._learning_repo is not None
            and self._learning_repo.get_lesson(user_id, lesson_id) is None
        ):
            raise AppError(404, "NOT_FOUND", "Leçon associée introuvable.")
        if (
            skill_id is not None
            and self._skill_repo is not None
            and self._skill_repo.get_skill(user_id, skill_id) is None
        ):
            raise AppError(404, "NOT_FOUND", "Compétence associée introuvable.")

    def list_sessions(
        self,
        user_id: UUID,
        *,
        status_filter: SessionStatus | None = None,
    ) -> list[SessionResponse]:
        records = self._session_repo.list_by_user(user_id)
        if status_filter is not None:
            records = [item for item in records if item.status == status_filter]
        records.sort(key=lambda item: item.started_at, reverse=True)
        return [to_session_response(item) for item in records]

    def create_session(self, user_id: UUID, payload: SessionCreate) -> SessionResponse:
        self._validate_task_ownership(user_id, payload.task_id)
        self._validate_palier2_links(
            user_id,
            project_id=payload.project_id,
            module_id=payload.module_id,
            lesson_id=payload.lesson_id,
            skill_id=payload.skill_id,
        )
        now = datetime.now(timezone.utc)
        started_at = payload.started_at or now
        is_completed = payload.ended_at is not None

        record = SessionRecord(
            id=uuid4(),
            user_id=user_id,
            title=payload.title,
            category=payload.category,
            status=SessionStatus.completed if is_completed else SessionStatus.in_progress,
            started_at=started_at,
            ended_at=payload.ended_at,
            result=payload.result,
            task_id=payload.task_id,
            project_id=payload.project_id,
            module_id=payload.module_id,
            lesson_id=payload.lesson_id,
            skill_id=payload.skill_id,
            created_at=now,
            updated_at=now,
        )
        saved = self._session_repo.save(record)
        return to_session_response(saved)

    def finish_session(
        self,
        user_id: UUID,
        session_id: UUID,
        payload: SessionFinish,
    ) -> SessionResponse:
        existing = self._session_repo.get(user_id, session_id)
        if existing is None:
            raise AppError(404, "NOT_FOUND", "Séance introuvable.")

        if existing.status != SessionStatus.in_progress:
            raise AppError(409, "CONFLICT", "Seule une séance en cours peut être terminée.")

        now = datetime.now(timezone.utc)
        ended_at = payload.ended_at or now
        if ended_at <= existing.started_at:
            raise AppError(
                422,
                "VALIDATION_ERROR",
                "L’heure de fin doit être postérieure au début de la séance.",
            )

        updated = existing.model_copy(
            update={
                "status": SessionStatus.completed,
                "ended_at": ended_at,
                "result": payload.result,
                "updated_at": now,
            }
        )
        saved = self._session_repo.save(updated)
        return to_session_response(saved)

    def update_session(
        self,
        user_id: UUID,
        session_id: UUID,
        payload: SessionUpdate,
    ) -> SessionResponse:
        existing = self._session_repo.get(user_id, session_id)
        if existing is None:
            raise AppError(404, "NOT_FOUND", "Séance introuvable.")

        fields = payload.model_fields_set
        updates: dict[str, object] = {"updated_at": datetime.now(timezone.utc)}

        if "task_id" in fields:
            self._validate_task_ownership(user_id, payload.task_id)
            updates["task_id"] = payload.task_id
        if "project_id" in fields:
            self._validate_palier2_links(user_id, project_id=payload.project_id)
            updates["project_id"] = payload.project_id
        if "module_id" in fields:
            self._validate_palier2_links(user_id, module_id=payload.module_id)
            updates["module_id"] = payload.module_id
        if "lesson_id" in fields:
            self._validate_palier2_links(user_id, lesson_id=payload.lesson_id)
            updates["lesson_id"] = payload.lesson_id
        if "skill_id" in fields:
            self._validate_palier2_links(user_id, skill_id=payload.skill_id)
            updates["skill_id"] = payload.skill_id

        if "title" in fields and payload.title is not None:
            updates["title"] = payload.title
        if "category" in fields and payload.category is not None:
            updates["category"] = payload.category
        if "result" in fields:
            updates["result"] = payload.result

        if "status" in fields and payload.status is not None:
            if payload.status == SessionStatus.cancelled:
                updates["status"] = SessionStatus.cancelled
                updates["ended_at"] = None
            elif payload.status == SessionStatus.completed and existing.ended_at is None:
                raise AppError(
                    422,
                    "VALIDATION_ERROR",
                    "Utilisez /finish pour clôturer une séance avec un résultat.",
                )
            else:
                updates["status"] = payload.status

        saved = self._session_repo.save(existing.model_copy(update=updates))
        return to_session_response(saved)

    def delete_session(self, user_id: UUID, session_id: UUID) -> None:
        if not self._session_repo.delete(user_id, session_id):
            raise AppError(404, "NOT_FOUND", "Séance introuvable.")
