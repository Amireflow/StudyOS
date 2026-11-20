from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field
from app.schemas.common import ProjectStatus, TaskPriority
from app.schemas.schedule import ScheduleEventResponse
from app.schemas.sessions import SessionResponse, SessionSummary
from app.schemas.tasks import TaskResponse, TaskSummary


class DashboardActivePriority(BaseModel):
    title: str | None = None
    task_id: UUID | None = None
    project_id: UUID | None = None


class DashboardProjectItem(BaseModel):
    id: UUID
    name: str
    status: ProjectStatus
    priority: TaskPriority
    next_action: str = ""
    target_date: datetime | None = None


class DashboardCoursesProgress(BaseModel):
    total_courses: int = 0
    active_courses: int = 0
    completed_levels: int = 0
    total_levels: int = 0
    completed_lessons: int = 0
    total_lessons: int = 0
    completion_rate: int = 0


class DashboardSkillsProgress(BaseModel):
    total_skills: int = 0
    validated_skills: int = 0
    in_progress_skills: int = 0
    avg_level: float = 0.0


class DashboardDeadlineItem(BaseModel):
    kind: Literal["task", "project"]
    id: UUID
    title: str
    due_at: datetime
    priority: TaskPriority
    overdue: bool = False


class DashboardWeeklyStudyMetrics(BaseModel):
    real_study_minutes_7d: int = 0
    planned_schedule_minutes_7d: int = 0
    completed_sessions_7d: int = 0
    completion_ratio_pct: int = 0


class DashboardConsistencyStreak(BaseModel):
    current_streak_days: int = 0
    active_days_7d: int = 0


class DashboardBlockerAlert(BaseModel):
    code: str
    severity: Literal["info", "warning", "error"]
    message: str


class DashboardRecommendedAction(BaseModel):
    kind: str
    title: str
    reason: str
    target_id: UUID | None = None


class DashboardResponse(BaseModel):
    timezone: str
    active_priority: DashboardActivePriority
    today_events: list[ScheduleEventResponse]
    priority_tasks: list[TaskResponse]
    task_summary: TaskSummary
    session_summary: SessionSummary
    recent_completed_sessions: list[SessionResponse]
    in_progress_sessions: list[SessionResponse]
    critical_tasks: list[TaskResponse] = Field(default_factory=list)
    active_projects: list[DashboardProjectItem] = Field(default_factory=list)
    active_projects_count: int = 0
    paused_projects_count: int = 0
    courses_progress: DashboardCoursesProgress = Field(default_factory=DashboardCoursesProgress)
    skills_progress: DashboardSkillsProgress = Field(default_factory=DashboardSkillsProgress)
    today_schedule: list[ScheduleEventResponse] = Field(default_factory=list)
    upcoming_deadlines: list[DashboardDeadlineItem] = Field(default_factory=list)
    weekly_study_metrics: DashboardWeeklyStudyMetrics = Field(
        default_factory=DashboardWeeklyStudyMetrics
    )
    consistency_streak: DashboardConsistencyStreak = Field(
        default_factory=DashboardConsistencyStreak
    )
    blockers_and_alerts: list[DashboardBlockerAlert] = Field(default_factory=list)
    next_recommended_action: DashboardRecommendedAction | None = None
