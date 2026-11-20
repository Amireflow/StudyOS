from datetime import datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo
from app.repositories.courses_sql import SqlCourseRepository
from app.repositories.learning_sql import SqlProjectRepository, SqlSkillRepository
from app.repositories.memory import ScheduleRepository, SessionRepository, TaskRepository
from app.schemas.common import (
    CourseLessonStatus,
    CourseLevelStatus,
    CourseStatus,
    ProjectStatus,
    SessionStatus,
    TaskPriority,
)
from app.schemas.dashboard import (
    DashboardActivePriority,
    DashboardBlockerAlert,
    DashboardConsistencyStreak,
    DashboardCoursesProgress,
    DashboardDeadlineItem,
    DashboardProjectItem,
    DashboardRecommendedAction,
    DashboardResponse,
    DashboardSkillsProgress,
    DashboardWeeklyStudyMetrics,
)
from app.schemas.tasks import TaskResponse
from app.services.profile_service import ProfileService
from app.services.schedule_service import enrich_schedule_events
from app.services.sessions_service import (
    compute_session_duration_minutes,
    compute_session_summary,
    to_session_response,
)
from app.services.tasks_service import (
    PRIORITY_WEIGHT,
    compute_task_summary,
    is_active_task_status,
    is_task_overdue,
    sort_tasks_by_urgency,
)


class DashboardService:
    def __init__(
        self,
        profile_service: ProfileService,
        task_repo: TaskRepository,
        schedule_repo: ScheduleRepository,
        session_repo: SessionRepository,
        project_repo: SqlProjectRepository | None = None,
        course_repo: SqlCourseRepository | None = None,
        skill_repo: SqlSkillRepository | None = None,
    ) -> None:
        self._profile_service = profile_service
        self._task_repo = task_repo
        self._schedule_repo = schedule_repo
        self._session_repo = session_repo
        self._project_repo = project_repo
        self._course_repo = course_repo
        self._skill_repo = skill_repo

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
        window_start_utc = reference_now - timedelta(days=7)

        all_events = self._schedule_repo.list_by_user(user_id)
        today_event_records = [
            event
            for event in all_events
            if event.starts_at.astimezone(tz).date() == today_local
        ]
        today_events = enrich_schedule_events(today_event_records, all_events)

        all_tasks = self._task_repo.list_by_user(user_id)
        active_task_records = sort_tasks_by_urgency(
            [task for task in all_tasks if is_active_task_status(task.status)],
            profile.timezone,
            reference_now,
        )
        priority_tasks = [
            TaskResponse.model_validate(task.model_dump()) for task in active_task_records[:5]
        ]
        critical_tasks = [
            TaskResponse.model_validate(task.model_dump())
            for task in active_task_records
            if task.priority == TaskPriority.critical
        ][:3]
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

        # Projets actifs strictement (exclut planned, paused, blocked, completed, archived)
        all_projects = self._project_repo.list_projects(user_id) if self._project_repo is not None else []
        active_project_records = sorted(
            [p for p in all_projects if p.status == ProjectStatus.active],
            key=lambda p: (-PRIORITY_WEIGHT[p.priority], -p.created_at.timestamp()),
        )
        paused_projects_count = sum(1 for p in all_projects if p.status == ProjectStatus.paused)
        blocked_projects = [p for p in all_projects if p.status == ProjectStatus.blocked]
        active_projects = [
            DashboardProjectItem(
                id=p.id,
                name=p.name,
                status=p.status,
                priority=p.priority,
                next_action=p.next_action,
                target_date=p.target_date,
            )
            for p in active_project_records
        ]

        # Cours & leçons
        if self._course_repo is not None:
            all_courses = self._course_repo.list_courses(user_id)
            all_levels = self._course_repo.list_levels(user_id)
            all_course_lessons = self._course_repo.list_lessons(user_id)
            total_lessons = len(all_course_lessons)
            completed_lessons = sum(
                1 for lesson in all_course_lessons if lesson.status == CourseLessonStatus.completed
            )
            courses_progress = DashboardCoursesProgress(
                total_courses=len(all_courses),
                active_courses=sum(1 for c in all_courses if c.status == CourseStatus.active),
                completed_levels=sum(
                    1 for lv in all_levels if lv.status == CourseLevelStatus.validated
                ),
                total_levels=len(all_levels),
                completed_lessons=completed_lessons,
                total_lessons=total_lessons,
                completion_rate=0 if total_lessons == 0 else round((completed_lessons / total_lessons) * 100),
            )
        else:
            all_course_lessons = []
            courses_progress = DashboardCoursesProgress()

        # Compétences
        if self._skill_repo is not None:
            all_skills = self._skill_repo.list_skills(user_id)
            total_skills = len(all_skills)
            validated_skills = sum(
                1
                for s in all_skills
                if (s.target_level is not None and s.current_level >= s.target_level)
                or (s.target_level is None and s.current_level >= 3)
            )
            in_progress_skills = sum(
                1
                for s in all_skills
                if s.current_level > 0
                and not (
                    (s.target_level is not None and s.current_level >= s.target_level)
                    or (s.target_level is None and s.current_level >= 3)
                )
            )
            avg_level = (
                round(sum(s.current_level for s in all_skills) / total_skills, 2)
                if total_skills > 0
                else 0.0
            )
            skills_progress = DashboardSkillsProgress(
                total_skills=total_skills,
                validated_skills=validated_skills,
                in_progress_skills=in_progress_skills,
                avg_level=avg_level,
            )
        else:
            skills_progress = DashboardSkillsProgress()

        # Échéances à venir (tâches actives + projets actifs/planifiés/bloqués)
        deadlines: list[DashboardDeadlineItem] = []
        for task in active_task_records:
            if task.due_at is not None:
                deadlines.append(
                    DashboardDeadlineItem(
                        kind="task",
                        id=task.id,
                        title=task.title,
                        due_at=task.due_at,
                        priority=task.priority,
                        overdue=is_task_overdue(task, profile.timezone, reference_now),
                    )
                )
        for project in all_projects:
            if (
                project.target_date is not None
                and project.status in {ProjectStatus.active, ProjectStatus.planned, ProjectStatus.blocked}
            ):
                deadlines.append(
                    DashboardDeadlineItem(
                        kind="project",
                        id=project.id,
                        title=project.name,
                        due_at=project.target_date,
                        priority=project.priority,
                        overdue=project.target_date.astimezone(tz).date() < today_local,
                    )
                )
        deadlines.sort(key=lambda item: item.due_at)
        upcoming_deadlines = deadlines[:6]

        # Métriques hebdomadaires (réel vs planifié, séances annulées exclues)
        completed_sessions_7d = [
            s
            for s in completed_sessions
            if window_start_utc <= (s.ended_at or s.started_at) <= reference_now
        ]
        real_study_minutes_7d = sum(
            compute_session_duration_minutes(s) for s in completed_sessions_7d
        )
        planned_schedule_minutes_7d = 0
        for ev in all_events:
            if ev.ends_at > window_start_utc and ev.starts_at < reference_now:
                clipped_start = max(ev.starts_at, window_start_utc)
                clipped_end = min(ev.ends_at, reference_now)
                planned_schedule_minutes_7d += max(
                    0, round((clipped_end - clipped_start).total_seconds() / 60)
                )
        completion_ratio_pct = (
            0
            if planned_schedule_minutes_7d == 0
            else min(100, round((real_study_minutes_7d / planned_schedule_minutes_7d) * 100))
        )
        weekly_study_metrics = DashboardWeeklyStudyMetrics(
            real_study_minutes_7d=real_study_minutes_7d,
            planned_schedule_minutes_7d=planned_schedule_minutes_7d,
            completed_sessions_7d=len(completed_sessions_7d),
            completion_ratio_pct=completion_ratio_pct,
        )

        # Régularité / streak local
        study_dates = {
            (s.ended_at or s.started_at).astimezone(tz).date() for s in completed_sessions
        }
        active_days_7d = sum(
            1 for offset in range(7) if (today_local - timedelta(days=offset)) in study_dates
        )
        streak_days = 0
        cursor = today_local if today_local in study_dates else today_local - timedelta(days=1)
        while cursor in study_dates:
            streak_days += 1
            cursor = cursor - timedelta(days=1)
        consistency_streak = DashboardConsistencyStreak(
            current_streak_days=streak_days,
            active_days_7d=active_days_7d,
        )

        # Blocages & alertes
        blockers_and_alerts: list[DashboardBlockerAlert] = []
        if task_summary.overdue_count > 0:
            blockers_and_alerts.append(
                DashboardBlockerAlert(
                    code="OVERDUE_TASKS",
                    severity="warning",
                    message=f"{task_summary.overdue_count} tâche(s) en retard requièrent une action.",
                )
            )
        today_conflicts = sum(1 for ev in today_events if ev.has_conflict)
        if today_conflicts > 0:
            blockers_and_alerts.append(
                DashboardBlockerAlert(
                    code="SCHEDULE_CONFLICTS_TODAY",
                    severity="warning",
                    message=f"{today_conflicts} créneau(x) en conflit dans l'agenda du jour.",
                )
            )
        if blocked_projects:
            blockers_and_alerts.append(
                DashboardBlockerAlert(
                    code="BLOCKED_PROJECTS",
                    severity="warning",
                    message=f"{len(blocked_projects)} projet(s) actuellement bloqué(s).",
                )
            )
        if not profile.active_priority_title and task_summary.active_count > 0:
            blockers_and_alerts.append(
                DashboardBlockerAlert(
                    code="NO_ACTIVE_PRIORITY",
                    severity="info",
                    message="Aucune priorité principale définie pour cadrer la journée.",
                )
            )

        # Prochaine action recommandée déterministe
        next_recommended_action: DashboardRecommendedAction | None = None
        if in_progress_sessions:
            current_session = in_progress_sessions[0]
            next_recommended_action = DashboardRecommendedAction(
                kind="session",
                title=f"Clôturer : {current_session.title}",
                reason="Une séance d'étude est actuellement en cours.",
                target_id=current_session.id,
            )
        else:
            priority_task = next(
                (t for t in active_task_records if t.id == profile.active_priority_task_id),
                None,
            )
            if priority_task is not None:
                next_recommended_action = DashboardRecommendedAction(
                    kind="task",
                    title=priority_task.title,
                    reason="Votre priorité principale active.",
                    target_id=priority_task.id,
                )
            elif active_task_records:
                top_task = active_task_records[0]
                is_overdue_top = is_task_overdue(top_task, profile.timezone, reference_now)
                next_recommended_action = DashboardRecommendedAction(
                    kind="task",
                    title=top_task.title,
                    reason="Tâche en retard prioritaire." if is_overdue_top else "Tâche active la plus urgente.",
                    target_id=top_task.id,
                )
            elif active_project_records:
                top_project = active_project_records[0]
                next_recommended_action = DashboardRecommendedAction(
                    kind="project",
                    title=top_project.next_action or top_project.name,
                    reason=f"Prochaine action du projet actif « {top_project.name} ».",
                    target_id=top_project.id,
                )
            else:
                next_lesson = next(
                    (
                        lesson
                        for lesson in all_course_lessons
                        if lesson.status != CourseLessonStatus.completed
                    ),
                    None,
                )
                if next_lesson is not None:
                    next_recommended_action = DashboardRecommendedAction(
                        kind="course_lesson",
                        title=next_lesson.title,
                        reason="Prochaine leçon à compléter dans vos cours.",
                        target_id=next_lesson.id,
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
            critical_tasks=critical_tasks,
            active_projects=active_projects,
            active_projects_count=len(active_projects),
            paused_projects_count=paused_projects_count,
            courses_progress=courses_progress,
            skills_progress=skills_progress,
            today_schedule=today_events,
            upcoming_deadlines=upcoming_deadlines,
            weekly_study_metrics=weekly_study_metrics,
            consistency_streak=consistency_streak,
            blockers_and_alerts=blockers_and_alerts,
            next_recommended_action=next_recommended_action,
        )
