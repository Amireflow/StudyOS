from datetime import datetime, timezone
from uuid import UUID
from zoneinfo import ZoneInfo
from app.repositories.memory import ScheduleRepository, SessionRepository, TaskRepository
from app.schemas.common import SessionStatus
from app.schemas.dashboard import DashboardActivePriority, DashboardResponse
from app.schemas.tasks import TaskResponse
from app.services.profile_service import ProfileService
from app.services.schedule_service import enrich_schedule_events
from app.services.sessions_service import compute_session_summary, to_session_response
from app.services.tasks_service import (
    compute_task_summary,
    is_active_task_status,
    sort_tasks_by_urgency,
)


class DashboardService:
    def __init__(
        self,
        profile_service: ProfileService,
        task_repo: TaskRepository,
        schedule_repo: ScheduleRepository,
        session_repo: SessionRepository,
    ) -> None:
        self._profile_service = profile_service
        self._task_repo = task_repo
        self._schedule_repo = schedule_repo
        self._session_repo = session_repo

    def get_dashboard(
        self,
        user_id: UUID,
        *,
        now_utc: datetime | None = None,
    ) -> DashboardResponse:
        profile = self._profile_service.get_or_create_record(user_id)
        tz = ZoneInfo(profile.timezone)
        reference_now = now_utc or datetime.now(timezone.utc)
        today_local = reference_now.astimezone(tz).date()

        all_events = self._schedule_repo.list_by_user(user_id)
        today_event_records = [
            event
            for event in all_events
            if event.starts_at.astimezone(tz).date() == today_local
        ]
        today_events = enrich_schedule_events(today_event_records, all_events)

        all_tasks = self._task_repo.list_by_user(user_id)
        active_tasks = sort_tasks_by_urgency(
            [task for task in all_tasks if is_active_task_status(task.status)]
        )
        priority_tasks = [TaskResponse.model_validate(task.model_dump()) for task in active_tasks[:5]]
        task_summary = compute_task_summary(all_tasks, profile.timezone, reference_now)

        all_sessions = self._session_repo.list_by_user(user_id)
        session_summary = compute_session_summary(all_sessions)
        completed_sessions = sorted(
            [
                session
                for session in all_sessions
                if session.status == SessionStatus.completed and session.ended_at is not None
            ],
            key=lambda session: session.started_at,
            reverse=True,
        )
        in_progress_sessions = sorted(
            [
                session
                for session in all_sessions
                if session.status == SessionStatus.in_progress
            ],
            key=lambda session: session.started_at,
            reverse=True,
        )

        return DashboardResponse(
            timezone=profile.timezone,
            active_priority=DashboardActivePriority(
                title=profile.active_priority_title,
                task_id=profile.active_priority_task_id,
                project_id=profile.active_priority_project_id,
            ),
            today_events=today_events,
            priority_tasks=priority_tasks,
            task_summary=task_summary,
            session_summary=session_summary,
            recent_completed_sessions=[
                to_session_response(session) for session in completed_sessions[:3]
            ],
            in_progress_sessions=[
                to_session_response(session) for session in in_progress_sessions
            ],
        )
