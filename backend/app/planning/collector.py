from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field
from app.repositories.ai_sql import SqlAiMemoryRepository, UserAiMemoryRecord
from app.repositories.courses_sql import (
    CourseLessonRecord,
    CourseLevelRecord,
    CourseRecord,
    CourseSubmissionRecord,
    SqlCourseRepository,
)
from app.repositories.learning_sql import (
    LearningModuleRecord,
    LearningPathRecord,
    LessonRecord,
    PersonalGoalRecord,
    ProjectRecord,
    SkillAssessmentRecord,
    SkillEvidenceRecord,
    SkillRecord,
    SqlLearningRepository,
    SqlPersonalGoalRepository,
    SqlProjectRepository,
    SqlSkillRepository,
)
from app.repositories.memory import (
    ProfileRecord,
    ProfileRepository,
    ScheduleEventRecord,
    ScheduleRepository,
    SessionRecord,
    SessionRepository,
    TaskRecord,
    TaskRepository,
)
from app.repositories.planning_sql import (
    LearningPlanVersionRecord,
    SqlPlanningRepository,
    UserAvailabilityRuleRecord,
)
from app.schemas.common import (
    CourseSessionSubtype,
    CourseStatus,
    LearningStatus,
    ObjectiveStatus,
    ProjectStatus,
    ScheduleEventSource,
    ScheduleEventType,
    SessionStatus,
    TaskStatus,
)


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def is_fixed_commitment_event(event: ScheduleEventRecord) -> bool:
    if event.type == ScheduleEventType.course:
        return True
    if event.source == ScheduleEventSource.timetable_import or event.import_id is not None:
        return True
    if event.session_subtype in (
        CourseSessionSubtype.cours,
        CourseSessionSubtype.td,
        CourseSessionSubtype.tp,
        CourseSessionSubtype.examen,
    ):
        return True
    if event.type in (ScheduleEventType.personal, ScheduleEventType.other) and event.source == ScheduleEventSource.manual:
        return True
    return False


def is_exam_event(event: ScheduleEventRecord) -> bool:
    if event.session_subtype == CourseSessionSubtype.examen:
        return True
    lowered = f"{event.title} {event.notes or ''}".lower()
    return any(tok in lowered for tok in ("examen", "partiel", "exam", "contrôle final", "midterm"))


class AcademicDifficultySignal(BaseModel):
    subject: str
    reason: str
    source_type: str
    source_id: str | None = None
    severity: float = 1.0


class PedagogicalWorkHistory(BaseModel):
    completed_sessions_count: int = 0
    cancelled_or_incomplete_count: int = 0
    total_completed_minutes_14d: int = 0
    avg_session_minutes: int = 60
    completion_rate: float = 1.0
    minutes_by_subject_14d: dict[str, int] = Field(default_factory=dict)
    recurring_difficulty_keywords: list[str] = Field(default_factory=list)


class PlanningContextSnapshot(BaseModel):
    user_id: UUID
    collected_at: datetime
    profile: ProfileRecord | None = None
    ai_memory: UserAiMemoryRecord | None = None
    timezone: str = "Europe/Paris"

    schedule_events: list[ScheduleEventRecord] = Field(default_factory=list)
    fixed_events: list[ScheduleEventRecord] = Field(default_factory=list)
    planned_learning_events: list[ScheduleEventRecord] = Field(default_factory=list)
    upcoming_exams: list[ScheduleEventRecord] = Field(default_factory=list)

    tasks: list[TaskRecord] = Field(default_factory=list)
    open_tasks: list[TaskRecord] = Field(default_factory=list)
    overdue_tasks: list[TaskRecord] = Field(default_factory=list)

    projects: list[ProjectRecord] = Field(default_factory=list)
    active_projects: list[ProjectRecord] = Field(default_factory=list)

    personal_goals: list[PersonalGoalRecord] = Field(default_factory=list)
    active_goals: list[PersonalGoalRecord] = Field(default_factory=list)

    skills: list[SkillRecord] = Field(default_factory=list)
    skill_evidence: list[SkillEvidenceRecord] = Field(default_factory=list)
    skill_assessments: list[SkillAssessmentRecord] = Field(default_factory=list)
    failed_assessments: list[SkillAssessmentRecord] = Field(default_factory=list)

    courses: list[CourseRecord] = Field(default_factory=list)
    active_courses: list[CourseRecord] = Field(default_factory=list)
    course_levels_by_course: dict[str, list[CourseLevelRecord]] = Field(default_factory=dict)
    course_lessons_by_course: dict[str, list[CourseLessonRecord]] = Field(default_factory=dict)
    course_submissions_by_course: dict[str, list[CourseSubmissionRecord]] = Field(
        default_factory=dict
    )
    failed_course_submissions: list[CourseSubmissionRecord] = Field(default_factory=list)

    learning_paths: list[LearningPathRecord] = Field(default_factory=list)
    active_learning_paths: list[LearningPathRecord] = Field(default_factory=list)
    modules_by_path: dict[str, list[LearningModuleRecord]] = Field(default_factory=dict)
    lessons_by_module: dict[str, list[LessonRecord]] = Field(default_factory=dict)

    availability_rules: list[UserAvailabilityRuleRecord] = Field(default_factory=list)
    plan_versions: list[LearningPlanVersionRecord] = Field(default_factory=list)
    applied_event_ids: list[str] = Field(default_factory=list)

    sessions: list[SessionRecord] = Field(default_factory=list)
    work_history: PedagogicalWorkHistory = Field(default_factory=PedagogicalWorkHistory)
    academic_difficulties: list[AcademicDifficultySignal] = Field(default_factory=list)


class PlanningContextCollector:
    """Agrège de manière déterministe les 6 sources de données StudyOS pour un utilisateur."""

    def __init__(
        self,
        *,
        profile_repo: ProfileRepository,
        schedule_repo: ScheduleRepository,
        task_repo: TaskRepository,
        session_repo: SessionRepository,
        project_repo: SqlProjectRepository | None = None,
        goal_repo: SqlPersonalGoalRepository | None = None,
        learning_repo: SqlLearningRepository | None = None,
        skill_repo: SqlSkillRepository | None = None,
        course_repo: SqlCourseRepository | None = None,
        ai_memory_repo: SqlAiMemoryRepository | None = None,
        planning_repo: SqlPlanningRepository | None = None,
    ) -> None:
        self._profile_repo = profile_repo
        self._schedule_repo = schedule_repo
        self._task_repo = task_repo
        self._session_repo = session_repo
        self._project_repo = project_repo
        self._goal_repo = goal_repo
        self._learning_repo = learning_repo
        self._skill_repo = skill_repo
        self._course_repo = course_repo
        self._ai_memory_repo = ai_memory_repo
        self._planning_repo = planning_repo

    def collect(
        self,
        user_id: UUID,
        *,
        now: datetime | None = None,
        timezone_override: str | None = None,
    ) -> PlanningContextSnapshot:
        current_utc = _ensure_utc(now) or datetime.now(timezone.utc)
        profile = self._profile_repo.get(user_id)
        ai_memory = self._ai_memory_repo.get(user_id) if self._ai_memory_repo else None
        tz_name = (
            timezone_override
            or (profile.timezone if profile and profile.timezone else None)
            or "Europe/Paris"
        )

        # A + E. Événements du calendrier
        schedule_events = list(self._schedule_repo.list_by_user(user_id))
        schedule_events.sort(key=lambda e: _ensure_utc(e.starts_at) or current_utc)

        plan_versions = (
            self._planning_repo.list_plan_versions(user_id, limit=20)
            if self._planning_repo
            else []
        )
        applied_event_ids: list[str] = []
        latest_applied = next(
            (v for v in plan_versions if v.status.value in ("applied", "restored")),
            None,
        )
        if latest_applied is not None:
            applied_event_ids = list(latest_applied.applied_event_ids)

        fixed_events: list[ScheduleEventRecord] = []
        planned_learning_events: list[ScheduleEventRecord] = []
        upcoming_exams: list[ScheduleEventRecord] = []
        applied_id_set = set(applied_event_ids)
        for ev in schedule_events:
            ev_end = _ensure_utc(ev.ends_at) or current_utc
            if is_exam_event(ev) and ev_end >= current_utc - timedelta(hours=2):
                upcoming_exams.append(ev)
            if is_fixed_commitment_event(ev):
                fixed_events.append(ev)
            elif (
                str(ev.id) in applied_id_set
                or ev.source == ScheduleEventSource.ai_proposal
                or ev.type in (ScheduleEventType.learning, ScheduleEventType.project)
            ):
                planned_learning_events.append(ev)
                if ev.source == ScheduleEventSource.manual and str(ev.id) not in applied_id_set:
                    # Un événement manuel explicitement posé par l'utilisateur bloque aussi ce créneau
                    fixed_events.append(ev)
            else:
                fixed_events.append(ev)

        # D. Tâches & projets
        tasks = list(self._task_repo.list_by_user(user_id))
        open_tasks = [
            t for t in tasks if t.status in (TaskStatus.todo, TaskStatus.in_progress)
        ]
        overdue_tasks = [
            t
            for t in open_tasks
            if t.due_at is not None and (_ensure_utc(t.due_at) or current_utc) < current_utc
        ]

        projects = self._project_repo.list_projects(user_id) if self._project_repo else []
        active_projects = [
            p for p in projects if p.status in (ProjectStatus.planned, ProjectStatus.active)
        ]

        # B. Objectifs personnels & compétences
        personal_goals = self._goal_repo.list_goals(user_id) if self._goal_repo else []
        active_goals = [
            g
            for g in personal_goals
            if g.status in (ObjectiveStatus.active, ObjectiveStatus.planned)
        ]

        skills = self._skill_repo.list_skills(user_id) if self._skill_repo else []
        skill_evidence = self._skill_repo.list_evidence(user_id) if self._skill_repo else []
        skill_assessments = self._skill_repo.list_assessments(user_id) if self._skill_repo else []
        failed_assessments = [a for a in skill_assessments if a.passed is False]

        # C. Parcours & Cours intelligents
        courses = self._course_repo.list_courses(user_id) if self._course_repo else []
        active_courses = [c for c in courses if c.status == CourseStatus.active]
        course_levels_by_course: dict[str, list[CourseLevelRecord]] = {}
        course_lessons_by_course: dict[str, list[CourseLessonRecord]] = {}
        course_submissions_by_course: dict[str, list[CourseSubmissionRecord]] = {}
        failed_course_submissions: list[CourseSubmissionRecord] = []

        if self._course_repo is not None:
            for course in courses:
                cid = str(course.id)
                levels = sorted(
                    self._course_repo.list_levels(user_id, course_id=course.id),
                    key=lambda lv: lv.level_number,
                )
                lessons = sorted(
                    self._course_repo.list_lessons(user_id, course_id=course.id),
                    key=lambda ls: ls.position,
                )
                subs = self._course_repo.list_submissions(user_id, course_id=course.id)
                course_levels_by_course[cid] = levels
                course_lessons_by_course[cid] = lessons
                course_submissions_by_course[cid] = subs
                for sub in subs:
                    if sub.passed is False or (sub.score is not None and sub.score < 70):
                        failed_course_submissions.append(sub)

        learning_paths = self._learning_repo.list_paths(user_id) if self._learning_repo else []
        active_learning_paths = [
            lp
            for lp in learning_paths
            if lp.status in (LearningStatus.not_started, LearningStatus.active)
        ]
        modules_by_path: dict[str, list[LearningModuleRecord]] = {}
        lessons_by_module: dict[str, list[LessonRecord]] = {}
        if self._learning_repo is not None:
            all_modules = self._learning_repo.list_modules(user_id)
            for mod in sorted(all_modules, key=lambda m: m.position):
                modules_by_path.setdefault(str(mod.path_id), []).append(mod)
            all_lessons = self._learning_repo.list_lessons(user_id)
            for les in sorted(all_lessons, key=lambda l: l.position):
                lessons_by_module.setdefault(str(les.module_id), []).append(les)

        # E. Règles de disponibilité explicites
        availability_rules = (
            self._planning_repo.list_availability_rules(user_id, active_only=True)
            if self._planning_repo
            else []
        )

        # F. Historique de travail réel
        sessions = list(self._session_repo.list_by_user(user_id))
        work_history = self._build_work_history(sessions, current_utc)
        difficulties = self._collect_difficulty_signals(
            skills=skills,
            failed_assessments=failed_assessments,
            courses=courses,
            failed_submissions=failed_course_submissions,
            open_tasks=open_tasks,
            ai_memory=ai_memory,
        )

        return PlanningContextSnapshot(
            user_id=user_id,
            collected_at=current_utc,
            profile=profile,
            ai_memory=ai_memory,
            timezone=tz_name,
            schedule_events=schedule_events,
            fixed_events=fixed_events,
            planned_learning_events=planned_learning_events,
            upcoming_exams=upcoming_exams,
            tasks=tasks,
            open_tasks=open_tasks,
            overdue_tasks=overdue_tasks,
            projects=projects,
            active_projects=active_projects,
            personal_goals=personal_goals,
            active_goals=active_goals,
            skills=skills,
            skill_evidence=skill_evidence,
            skill_assessments=skill_assessments,
            failed_assessments=failed_assessments,
            courses=courses,
            active_courses=active_courses,
            course_levels_by_course=course_levels_by_course,
            course_lessons_by_course=course_lessons_by_course,
            course_submissions_by_course=course_submissions_by_course,
            failed_course_submissions=failed_course_submissions,
            learning_paths=learning_paths,
            active_learning_paths=active_learning_paths,
            modules_by_path=modules_by_path,
            lessons_by_module=lessons_by_module,
            availability_rules=availability_rules,
            plan_versions=plan_versions,
            applied_event_ids=applied_event_ids,
            sessions=sessions,
            work_history=work_history,
            academic_difficulties=difficulties,
        )

    def _build_work_history(
        self,
        sessions: list[SessionRecord],
        current_utc: datetime,
    ) -> PedagogicalWorkHistory:
        window_start = current_utc - timedelta(days=14)
        completed_count = 0
        cancelled_count = 0
        total_minutes = 0
        recent_durations: list[int] = []
        by_subject: dict[str, int] = {}
        difficulty_notes: list[str] = []

        for sess in sessions:
            started = _ensure_utc(sess.started_at) or current_utc
            if sess.status == SessionStatus.completed:
                completed_count += 1
                if started >= window_start:
                    mins = 0
                    if sess.ended_at is not None:
                        ended = _ensure_utc(sess.ended_at) or started
                        mins = max(0, int((ended - started).total_seconds() // 60))
                    if mins > 0:
                        total_minutes += mins
                        recent_durations.append(mins)
                        cat = (sess.category or sess.title or "general").strip().lower()
                        by_subject[cat] = by_subject.get(cat, 0) + mins
            elif sess.status == SessionStatus.cancelled:
                cancelled_count += 1

            combined = (
                f"{sess.title} {sess.result or ''} {sess.blockers or ''} {sess.actual_activity or ''}".lower()
            )
            if any(k in combined for k in ("bloqué", "difficile", "échec", "raté", "incompris")):
                difficulty_notes.append(sess.title)

        total_attempts = completed_count + cancelled_count
        completion_rate = (completed_count / total_attempts) if total_attempts > 0 else 1.0
        avg_minutes = (
            int(round(sum(recent_durations) / len(recent_durations)))
            if recent_durations
            else 60
        )
        avg_minutes = max(30, min(avg_minutes, 120))
        return PedagogicalWorkHistory(
            completed_sessions_count=completed_count,
            cancelled_or_incomplete_count=cancelled_count,
            total_completed_minutes_14d=total_minutes,
            avg_session_minutes=avg_minutes,
            completion_rate=round(completion_rate, 2),
            minutes_by_subject_14d=by_subject,
            recurring_difficulty_keywords=difficulty_notes[:10],
        )

    def _collect_difficulty_signals(
        self,
        *,
        skills: list[SkillRecord],
        failed_assessments: list[SkillAssessmentRecord],
        courses: list[CourseRecord],
        failed_submissions: list[CourseSubmissionRecord],
        open_tasks: list[TaskRecord],
        ai_memory: UserAiMemoryRecord | None,
    ) -> list[AcademicDifficultySignal]:
        signals: list[AcademicDifficultySignal] = []
        skill_by_id = {s.id: s for s in skills}
        course_by_id = {c.id: c for c in courses}

        for ass in failed_assessments:
            sk = skill_by_id.get(ass.skill_id)
            subj = sk.name if sk else ass.prompt_title
            gaps = ", ".join(ass.gaps_identified[:2]) if ass.gaps_identified else (ass.remediation_recommendation or "Évaluation non validée")
            signals.append(
                AcademicDifficultySignal(
                    subject=subj,
                    reason=gaps,
                    source_type="skill_assessment",
                    source_id=str(ass.id),
                    severity=1.4,
                )
            )

        for sub in failed_submissions:
            c = course_by_id.get(sub.course_id)
            subj = c.subject if c else sub.title
            detail = "; ".join(sub.improvements[:2]) if sub.improvements else (sub.next_step_hint or f"Score {sub.score or 0}/100")
            signals.append(
                AcademicDifficultySignal(
                    subject=subj,
                    reason=detail,
                    source_type="course_submission",
                    source_id=str(sub.id),
                    severity=1.3,
                )
            )

        now_utc = datetime.now(timezone.utc)
        for task in open_tasks:
            due = _ensure_utc(task.due_at)
            if due is not None and due < now_utc and task.priority.value in ("critical", "high"):
                signals.append(
                    AcademicDifficultySignal(
                        subject=task.title,
                        reason="Tâche critique ou haute en retard",
                        source_type="task",
                        source_id=str(task.id),
                        severity=1.2,
                    )
                )

        if ai_memory and ai_memory.academic_context:
            weak_subjects = ai_memory.academic_context.get("difficulties") or []
            if isinstance(weak_subjects, list):
                for item in weak_subjects[:5]:
                    text = str(item).strip()
                    if text:
                        signals.append(
                            AcademicDifficultySignal(
                                subject=text,
                                reason="Difficulté académique déclarée",
                                source_type="academic_context",
                                severity=1.25,
                            )
                        )
        return signals
