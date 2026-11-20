from uuid import UUID
from pydantic import BaseModel
from app.schemas.schedule import ScheduleEventResponse
from app.schemas.sessions import SessionResponse, SessionSummary
from app.schemas.tasks import TaskResponse, TaskSummary


class DashboardActivePriority(BaseModel):
    title: str | None = None
    task_id: UUID | None = None
    project_id: UUID | None = None


class DashboardResponse(BaseModel):
    timezone: str
    active_priority: DashboardActivePriority
    today_events: list[ScheduleEventResponse]
    priority_tasks: list[TaskResponse]
    task_summary: TaskSummary
    session_summary: SessionSummary
    recent_completed_sessions: list[SessionResponse]
    in_progress_sessions: list[SessionResponse]
