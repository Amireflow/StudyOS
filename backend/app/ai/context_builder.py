from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo
from pydantic import BaseModel, Field
from app.repositories.learning_sql import (
    SqlLearningRepository,
    SqlProjectRepository,
    SqlSkillRepository,
)
from app.repositories.memory import (
    ProfileRepository,
    ScheduleRepository,
    SessionRepository,
    TaskRepository,
)
from app.schemas.common import AiContextScope, SessionStatus, TaskStatus
from app.services.profile_service import ProfileService
from app.services.sessions_service import compute_session_duration_minutes
from app.services.tasks_service import is_active_task_status, is_task_overdue, sort_tasks_by_urgency

MAX_CONTEXT_TASKS = 10
MAX_CONTEXT_EVENTS = 8
MAX_CONTEXT_SESSIONS = 8
MAX_CONTEXT_PROJECTS = 6
MAX_CONTEXT_SKILLS = 10
MAX_CONTEXT_PATHS = 5


class BoundedUserContext(BaseModel):
    included_scopes: list[str]
    profile: dict[str, Any]
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    schedule_events: list[dict[str, Any]] = Field(default_factory=list)
    learning: dict[str, Any] = Field(default_factory=dict)
    skills: list[dict[str, Any]] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)
    recent_sessions: list[dict[str, Any]] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)
    missing_data: list[str] = Field(default_factory=list)
    is_partial_data: bool = False


def infer_scopes_from_message(
    message: str,
    explicit_scopes: list[AiContextScope] | None = None,
) -> set[str]:
    if explicit_scopes and AiContextScope.auto not in explicit_scopes:
        return {scope.value for scope in explicit_scopes}

    lowered = message.lower()
    scopes: set[str] = {"today", "tasks"}

    if any(word in lowered for word in ("créneau", "planning", "agenda", "horaire", "demain", "semaine", "cours")):
        scopes.add("schedule")
    if any(word in lowered for word in ("parcours", "module", "leçon", "apprendre", "exercice", "cours", "notion")):
        scopes.add("learning")
    if any(word in lowered for word in ("compétence", "preuve", "niveau", "maîtrise", "évaluer")):
        scopes.add("skills")
    if any(word in lowered for word in ("projet", "livrable", "prochaine action", "dispersion")):
        scopes.add("projects")
    if any(word in lowered for word in ("bilan", "hebdo", "semaine", "séance", "temps", "progression")):
        scopes.update({"weekly", "schedule", "projects", "learning", "skills"})

    return scopes


class ContextBuilder:
    """Sélectionne uniquement les données utiles et autorisées de l'utilisateur (AI-05, AI-06)."""

    def __init__(
        self,
        *,
        profile_service: ProfileService,
        task_repo: TaskRepository,
        schedule_repo: ScheduleRepository,
        session_repo: SessionRepository,
        learning_repo: SqlLearningRepository,
        skill_repo: SqlSkillRepository,
        project_repo: SqlProjectRepository,
    ) -> None:
        self._profile_service = profile_service
        self._task_repo = task_repo
        self._schedule_repo = schedule_repo
        self._session_repo = session_repo
        self._learning_repo = learning_repo
        self._skill_repo = skill_repo
        self._project_repo = project_repo

    def build_context(
        self,
        user_id: UUID,
        *,
        message: str = "",
        explicit_scopes: list[AiContextScope] | None = None,
        now_utc: datetime | None = None,
    ) -> BoundedUserContext:
        ref_now = now_utc or datetime.now(timezone.utc)
        scopes = infer_scopes_from_message(message, explicit_scopes)
        profile = self._profile_service.get_or_create_record(user_id)
        tz = ZoneInfo(profile.timezone)
        local_now = ref_now.astimezone(tz)
        today_date = local_now.date()
        week_ago_utc = ref_now - timedelta(days=7)

        missing_data: list[str] = []
        if not profile.active_priority_title:
            missing_data.append("Aucune priorité principale active définie.")

        all_tasks = self._task_repo.list_by_user(user_id)
        active_tasks = sort_tasks_by_urgency(
            [t for t in all_tasks if is_active_task_status(t.status)]
        )
        overdue_tasks = [t for t in active_tasks if is_task_overdue(t, profile.timezone, ref_now)]
        done_last_7d = [
            t
            for t in all_tasks
            if t.status == TaskStatus.done
            and t.completed_at is not None
            and t.completed_at >= week_ago_utc
        ]

        if not all_tasks:
            missing_data.append("Aucune tâche enregistrée.")

        tasks_payload = [
            {
                "id": str(t.id),
                "title": t.title,
                "status": t.status.value,
                "priority": t.priority.value,
                "due_at": t.due_at.isoformat() if t.due_at else None,
                "is_overdue": is_task_overdue(t, profile.timezone, ref_now),
            }
            for t in active_tasks[:MAX_CONTEXT_TASKS]
        ]

        schedule_payload: list[dict[str, Any]] = []
        if "schedule" in scopes or "today" in scopes or "weekly" in scopes:
            all_events = self._schedule_repo.list_by_user(user_id)
            relevant_events = [
                e
                for e in all_events
                if e.ends_at >= ref_now - timedelta(hours=12)
                and e.starts_at <= ref_now + timedelta(days=7)
            ]
            relevant_events.sort(key=lambda item: item.starts_at)
            if not relevant_events:
                missing_data.append("Aucun créneau planifié sur la période.")
            schedule_payload = [
                {
                    "id": str(e.id),
                    "title": e.title,
                    "type": e.type.value,
                    "starts_at": e.starts_at.isoformat(),
                    "ends_at": e.ends_at.isoformat(),
                    "is_today": e.starts_at.astimezone(tz).date() == today_date,
                }
                for e in relevant_events[:MAX_CONTEXT_EVENTS]
            ]

        learning_payload: dict[str, Any] = {}
        if "learning" in scopes or "weekly" in scopes:
            paths = self._learning_repo.list_paths(user_id)
            modules = self._learning_repo.list_modules(user_id)
            lessons = self._learning_repo.list_lessons(user_id)
            if not paths:
                missing_data.append("Aucun parcours d’apprentissage enregistré.")
            completed_lessons = sum(1 for l in lessons if l.status.value == "completed")
            learning_payload = {
                "paths": [
                    {
                        "id": str(p.id),
                        "title": p.title,
                        "goal": p.goal,
                        "status": p.status.value,
                    }
                    for p in paths[:MAX_CONTEXT_PATHS]
                ],
                "active_modules": [
                    {"id": str(m.id), "title": m.title, "status": m.status.value}
                    for m in modules[:MAX_CONTEXT_PATHS]
                ],
                "lessons_completed": completed_lessons,
                "lessons_total": len(lessons),
            }

        skills_payload: list[dict[str, Any]] = []
        if "skills" in scopes or "learning" in scopes or "weekly" in scopes:
            skills = self._skill_repo.list_skills(user_id)
            evidence = self._skill_repo.list_evidence(user_id)
            ev_count_by_skill: dict[UUID, int] = {}
            for ev in evidence:
                ev_count_by_skill[ev.skill_id] = ev_count_by_skill.get(ev.skill_id, 0) + 1
            if not skills and "skills" in scopes:
                missing_data.append("Aucune compétence enregistrée.")
            skills_payload = [
                {
                    "id": str(s.id),
                    "name": s.name,
                    "domain": s.domain,
                    "current_level": s.current_level,
                    "target_level": s.target_level,
                    "evidence_count": ev_count_by_skill.get(s.id, 0),
                }
                for s in skills[:MAX_CONTEXT_SKILLS]
            ]

        projects_payload: list[dict[str, Any]] = []
        if "projects" in scopes or "today" in scopes or "weekly" in scopes:
            projects = self._project_repo.list_projects(user_id)
            if not projects and "projects" in scopes:
                missing_data.append("Aucun projet enregistré.")
            projects_payload = [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "goal": p.goal,
                    "status": p.status.value,
                    "priority": p.priority.value,
                    "next_action": p.next_action,
                }
                for p in projects[:MAX_CONTEXT_PROJECTS]
            ]

        all_sessions = self._session_repo.list_by_user(user_id)
        completed_sessions_7d = [
            s
            for s in all_sessions
            if s.status == SessionStatus.completed
            and s.ended_at is not None
            and s.started_at >= week_ago_utc
        ]
        total_minutes_7d = sum(
            compute_session_duration_minutes(s, ref_now) for s in completed_sessions_7d
        )
        if not completed_sessions_7d and "weekly" in scopes:
            missing_data.append("Aucune séance d’étude terminée sur les 7 derniers jours.")

        recent_sessions_payload = [
            {
                "id": str(s.id),
                "title": s.title,
                "category": s.category,
                "duration_minutes": compute_session_duration_minutes(s, ref_now),
                "result": s.result,
                "started_at": s.started_at.isoformat(),
            }
            for s in sorted(completed_sessions_7d, key=lambda item: item.started_at, reverse=True)[
                :MAX_CONTEXT_SESSIONS
            ]
        ]

        return BoundedUserContext(
            included_scopes=sorted(scopes),
            profile={
                "display_name": profile.display_name,
                "timezone": profile.timezone,
                "local_date": today_date.isoformat(),
                "active_priority_title": profile.active_priority_title,
                "ai_instructions": profile.ai_instructions,
            },
            tasks=tasks_payload,
            schedule_events=schedule_payload,
            learning=learning_payload,
            skills=skills_payload,
            projects=projects_payload,
            recent_sessions=recent_sessions_payload,
            stats={
                "active_tasks_count": len(active_tasks),
                "overdue_tasks_count": len(overdue_tasks),
                "done_tasks_last_7d_count": len(done_last_7d),
                "completed_sessions_last_7d_count": len(completed_sessions_7d),
                "completed_minutes_last_7d": total_minutes_7d,
            },
            missing_data=missing_data,
            is_partial_data=len(missing_data) > 0,
        )
