from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4
from app.core.errors import AppError
from app.repositories.learning_sql import SkillEvidenceRecord
from app.repositories.memory import SessionRecord, SessionRepository, TaskRepository
from app.schemas.common import EvidenceVerificationStatus, SessionStatus, SkillEvidenceType
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
        goal_repo: Any | None = None,
    ) -> None:
        self._session_repo = session_repo
        self._task_repo = task_repo
        self._project_repo = project_repo
        self._learning_repo = learning_repo
        self._skill_repo = skill_repo
        self._goal_repo = goal_repo

    def _validate_task_ownership(self, user_id: UUID, task_id: UUID | None) -> None:
        if task_id is not None and self._task_repo.get(user_id, task_id) is None:
            raise AppError(404, "NOT_FOUND", "Tâche associée introuvable.")

    def _validate_palier2_links(
        self,
        user_id: UUID,
        *,
        project_id: UUID | None = None,
        goal_id: UUID | None = None,
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
            goal_id is not None
            and self._goal_repo is not None
            and self._goal_repo.get(user_id, goal_id) is None
        ):
            raise AppError(404, "NOT_FOUND", "Objectif personnel associé introuvable.")
        if (
            module_id is not None
            and self._learning_repo is not None
            and self._learning_repo.get_module(user_id, module_id) is None
        ):
            raise AppError(404, "NOT_FOUND", "Module associé introuvable.")
        lesson_rec = None
        if lesson_id is not None and self._learning_repo is not None:
            lesson_rec = self._learning_repo.get_lesson(user_id, lesson_id)
            if lesson_rec is None:
                raise AppError(404, "NOT_FOUND", "Leçon associée introuvable.")
        if module_id is not None and lesson_rec is not None and lesson_rec.module_id != module_id:
            raise AppError(
                422,
                "LESSON_MODULE_MISMATCH",
                "La leçon sélectionnée n'appartient pas au module associé.",
            )
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

    def _record_session_completion_feedback(
        self,
        user_id: UUID,
        record: SessionRecord,
    ) -> None:
        """Enregistre le retour d'exécution (durée réelle, difficultés, livrable/preuve) sur l'objectif ou projet lié."""
        if record.status != SessionStatus.completed or record.ended_at is None:
            return

        duration_min = compute_session_duration_minutes(record)
        now = record.updated_at
        history_entry: dict[str, Any] = {
            "timestamp": now.isoformat(),
            "event": "session_completed",
            "session_id": str(record.id),
            "planned_activity": record.planned_activity or record.title,
            "actual_activity": record.actual_activity or record.title,
            "result": record.result,
            "duration_minutes": duration_min,
            "outcome_status": record.outcome_status or "completed",
            "difficulties": record.blockers,
            "deliverable_summary": record.deliverable_summary,
            "next_step": record.next_step,
        }

        effective_skill_id = record.skill_id

        # 1. Mise à jour de l'objectif personnel lié (par goal_id ou par skill_id)
        if self._goal_repo is not None:
            target_goal = (
                self._goal_repo.get(user_id, record.goal_id)
                if record.goal_id is not None
                else None
            )
            if target_goal is None and record.skill_id is not None:
                all_goals = self._goal_repo.list_goals(user_id)
                target_goal = next(
                    (g for g in all_goals if g.skill_id == record.skill_id),
                    None,
                )
            if target_goal is not None:
                if effective_skill_id is None and target_goal.skill_id is not None:
                    effective_skill_id = target_goal.skill_id
                next_history = [*list(target_goal.progress_history or []), history_entry]
                goal_updates: dict[str, Any] = {
                    "progress_history": next_history,
                    "updated_at": now,
                }
                if record.next_step and len(record.next_step.strip()) >= 2:
                    goal_updates["next_action"] = record.next_step.strip()[:240]
                self._goal_repo.save(target_goal.model_copy(update=goal_updates))

        # 2. Mise à jour du projet lié
        if record.project_id is not None and self._project_repo is not None:
            project = self._project_repo.get(user_id, record.project_id)
            if project is not None:
                proj_history = [*list(project.progress_history or []), history_entry]
                proj_updates: dict[str, Any] = {
                    "progress_history": proj_history,
                    "updated_at": now,
                }
                if record.next_step and len(record.next_step.strip()) >= 2:
                    proj_updates["next_action"] = record.next_step.strip()[:240]
                self._project_repo.save(project.model_copy(update=proj_updates))

        # 3. Enregistrement automatique d'une preuve/livrable sur la compétence liée si fourni
        if (
            effective_skill_id is not None
            and self._skill_repo is not None
            and record.deliverable_summary
            and len(record.deliverable_summary.strip()) >= 5
        ):
            self._skill_repo.save_evidence(
                SkillEvidenceRecord(
                    id=uuid4(),
                    user_id=user_id,
                    skill_id=effective_skill_id,
                    type=SkillEvidenceType.deliverable,
                    description=record.deliverable_summary.strip()[:1000],
                    reference_url=None,
                    result=(record.result or "Séance terminée")[:200],
                    verification_status=EvidenceVerificationStatus.declared,
                    inspection_metadata={"source": "study_session", "session_id": str(record.id)},
                    inspected_at=now,
                    is_locked=False,
                    observed_at=now,
                    created_at=now,
                    updated_at=now,
                )
            )

    def create_session(self, user_id: UUID, payload: SessionCreate) -> SessionResponse:
        self._validate_task_ownership(user_id, payload.task_id)
        self._validate_palier2_links(
            user_id,
            project_id=payload.project_id,
            goal_id=payload.goal_id,
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
            planned_activity=payload.planned_activity or payload.title,
            actual_activity=payload.actual_activity or (payload.title if is_completed else None),
            outcome_status=payload.outcome_status or ("completed" if is_completed else None),
            deliverable_summary=payload.deliverable_summary,
            blockers=payload.blockers,
            next_step=payload.next_step,
            task_id=payload.task_id,
            project_id=payload.project_id,
            goal_id=payload.goal_id,
            module_id=payload.module_id,
            lesson_id=payload.lesson_id,
            skill_id=payload.skill_id,
            created_at=now,
            updated_at=now,
        )
        saved = self._session_repo.save(record)
        if is_completed:
            self._record_session_completion_feedback(user_id, saved)
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
                "planned_activity": payload.planned_activity or existing.planned_activity or existing.title,
                "actual_activity": payload.actual_activity or existing.actual_activity or existing.title,
                "outcome_status": payload.outcome_status or existing.outcome_status or "completed",
                "deliverable_summary": (
                    payload.deliverable_summary
                    if payload.deliverable_summary is not None
                    else existing.deliverable_summary
                ),
                "blockers": payload.blockers if payload.blockers is not None else existing.blockers,
                "next_step": payload.next_step if payload.next_step is not None else existing.next_step,
                "updated_at": now,
            }
        )
        saved = self._session_repo.save(updated)
        self._record_session_completion_feedback(user_id, saved)
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
        if "goal_id" in fields:
            self._validate_palier2_links(user_id, goal_id=payload.goal_id)
            updates["goal_id"] = payload.goal_id
        next_module_id = payload.module_id if "module_id" in fields else existing.module_id
        next_lesson_id = payload.lesson_id if "lesson_id" in fields else existing.lesson_id
        if "module_id" in fields and "lesson_id" not in fields:
            self._validate_palier2_links(user_id, module_id=payload.module_id, lesson_id=next_lesson_id)
            updates["module_id"] = payload.module_id
        elif "module_id" in fields and "lesson_id" in fields:
            self._validate_palier2_links(user_id, module_id=payload.module_id, lesson_id=payload.lesson_id)
            updates["module_id"] = payload.module_id
            updates["lesson_id"] = payload.lesson_id
        elif "lesson_id" in fields:
            self._validate_palier2_links(user_id, module_id=next_module_id, lesson_id=payload.lesson_id)
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
        if "planned_activity" in fields:
            updates["planned_activity"] = payload.planned_activity
        if "actual_activity" in fields:
            updates["actual_activity"] = payload.actual_activity
        if "outcome_status" in fields:
            updates["outcome_status"] = payload.outcome_status
        if "deliverable_summary" in fields:
            updates["deliverable_summary"] = payload.deliverable_summary
        if "blockers" in fields:
            updates["blockers"] = payload.blockers
        if "next_step" in fields:
            updates["next_step"] = payload.next_step

        next_status = existing.status
        if "status" in fields and payload.status is not None:
            if (
                existing.status == SessionStatus.completed
                and payload.status == SessionStatus.in_progress
            ):
                raise AppError(
                    409,
                    "SESSION_ALREADY_COMPLETED",
                    "Une séance déjà terminée ne peut pas être repassée en cours.",
                )
            if (
                existing.status == SessionStatus.cancelled
                and payload.status == SessionStatus.completed
            ):
                raise AppError(
                    409,
                    "CONFLICT",
                    "Une séance annulée ne peut pas passer directement au statut terminée.",
                )
            if payload.status == SessionStatus.cancelled:
                updates["status"] = SessionStatus.cancelled
                updates["ended_at"] = None
                next_status = SessionStatus.cancelled
            elif payload.status == SessionStatus.completed and existing.ended_at is None:
                raise AppError(
                    422,
                    "VALIDATION_ERROR",
                    "Utilisez /finish pour clôturer une séance avec un résultat.",
                )
            else:
                updates["status"] = payload.status
                next_status = payload.status

        if next_status == SessionStatus.completed and "result" in fields:
            if payload.result is None or len(payload.result.strip()) < 3:
                raise AppError(
                    422,
                    "VALIDATION_ERROR",
                    "Le résultat d'une séance terminée doit contenir au moins 3 caractères.",
                )

        saved = self._session_repo.save(existing.model_copy(update=updates))
        feedback_fields = {
            "result",
            "actual_activity",
            "outcome_status",
            "deliverable_summary",
            "blockers",
            "next_step",
            "goal_id",
            "project_id",
            "skill_id",
        }
        if saved.status == SessionStatus.completed and bool(fields & feedback_fields):
            self._record_session_completion_feedback(user_id, saved)
        return to_session_response(saved)

    def delete_session(self, user_id: UUID, session_id: UUID) -> None:
        if not self._session_repo.delete(user_id, session_id):
            raise AppError(404, "NOT_FOUND", "Séance introuvable.")
