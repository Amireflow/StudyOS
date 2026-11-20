from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo
from pydantic import BaseModel, Field
from app.repositories.ai_sql import SqlAiMemoryRepository, UserAiMemoryRecord
from app.repositories.courses_sql import SqlCourseRepository
from app.repositories.learning_sql import (
    SqlLearningRepository,
    SqlProjectRepository,
    SqlSkillRepository,
)
from app.repositories.memory import (
    ProfileRepository,
    ScheduleEventRecord,
    ScheduleRepository,
    SessionRepository,
    TaskRepository,
)
from app.schemas.common import (
    AiContextScope,
    LearningStatus,
    ProjectStatus,
    ScheduleEventSource,
    ScheduleEventType,
    SessionStatus,
    TaskPriority,
    TaskStatus,
)
from app.services.profile_service import ProfileService
from app.services.sessions_service import compute_session_duration_minutes
from app.services.tasks_service import is_active_task_status, is_task_overdue, sort_tasks_by_urgency

MAX_CONTEXT_TASKS = 10
MAX_CONTEXT_EVENTS = 40
MAX_CONTEXT_SESSIONS = 8
MAX_CONTEXT_PROJECTS = 6
MAX_CONTEXT_SKILLS = 10
MAX_CONTEXT_PATHS = 5
MAX_CONTEXT_COURSES = 5

DAY_NAMES_FR: tuple[str, ...] = (
    "Lundi",
    "Mardi",
    "Mercredi",
    "Jeudi",
    "Vendredi",
    "Samedi",
    "Dimanche",
)

_DAY_NAME_TO_WEEKDAY: dict[str, int] = {
    "lundi": 0,
    "monday": 0,
    "mon": 0,
    "mardi": 1,
    "tuesday": 1,
    "tue": 1,
    "mercredi": 2,
    "wednesday": 2,
    "wed": 2,
    "jeudi": 3,
    "thursday": 3,
    "thu": 3,
    "vendredi": 4,
    "friday": 4,
    "fri": 4,
    "samedi": 5,
    "saturday": 5,
    "sat": 5,
    "dimanche": 6,
    "sunday": 6,
    "sun": 6,
}


def _parse_availability_preferences(
    preferences: dict[str, Any] | None,
    memory: UserAiMemoryRecord | None = None,
) -> dict[str, Any]:
    prefs = preferences if isinstance(preferences, dict) else {}
    avail: dict[str, Any] = {}
    for key in (
        "study_start_hour",
        "study_end_hour",
        "preferred_session_minutes",
        "max_daily_study_minutes",
        "excluded_days",
        "weekly_study_hours",
    ):
        if key in prefs and prefs[key] is not None:
            avail[key] = prefs[key]
    raw_nested = prefs.get("availability")
    if isinstance(raw_nested, dict):
        for key, value in raw_nested.items():
            if value is not None:
                avail[key] = value
    if memory is not None:
        for key, value in (memory.availability_preferences or {}).items():
            if value is not None:
                avail[key] = value
        if memory.default_session_minutes:
            avail.setdefault("preferred_session_minutes", memory.default_session_minutes)
        if memory.weekly_study_hours is not None:
            avail["weekly_study_hours"] = memory.weekly_study_hours

    try:
        start_h = max(5, min(20, int(avail.get("study_start_hour", 8))))
    except (TypeError, ValueError):
        start_h = 8
    try:
        end_h = max(start_h + 1, min(23, int(avail.get("study_end_hour", 21))))
    except (TypeError, ValueError):
        end_h = max(start_h + 1, 21)
    try:
        pref_min = max(30, min(180, int(avail.get("preferred_session_minutes", 60))))
    except (TypeError, ValueError):
        pref_min = 60
    try:
        max_daily = max(60, min(480, int(avail.get("max_daily_study_minutes", 300))))
    except (TypeError, ValueError):
        max_daily = 300

    weekly_hours: int | None = None
    if avail.get("weekly_study_hours") is not None:
        try:
            weekly_hours = max(0, min(120, int(avail["weekly_study_hours"])))
        except (TypeError, ValueError):
            weekly_hours = None

    excluded: set[int] = set()
    for item in avail.get("excluded_days") or []:
        if isinstance(item, int) and 0 <= item <= 6:
            excluded.add(item)
        elif isinstance(item, str):
            s = item.strip().lower()
            if s.isdigit() and 0 <= int(s) <= 6:
                excluded.add(int(s))
            elif s in _DAY_NAME_TO_WEEKDAY:
                excluded.add(_DAY_NAME_TO_WEEKDAY[s])
    return {
        "study_start_hour": start_h,
        "study_end_hour": end_h,
        "preferred_session_minutes": pref_min,
        "max_daily_study_minutes": max_daily,
        "excluded_days": sorted(excluded),
        "weekly_study_hours": weekly_hours,
        "max_weekly_study_minutes": weekly_hours * 60 if weekly_hours is not None else None,
    }


class BoundedUserContext(BaseModel):
    included_scopes: list[str]
    profile: dict[str, Any]
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    schedule_events: list[dict[str, Any]] = Field(default_factory=list)
    university_courses: list[dict[str, Any]] = Field(default_factory=list)
    availability: dict[str, Any] = Field(default_factory=dict)
    strategic_analysis: dict[str, Any] = Field(default_factory=dict)
    learning: dict[str, Any] = Field(default_factory=dict)
    courses: list[dict[str, Any]] = Field(default_factory=list)
    skills: list[dict[str, Any]] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)
    personal_goals: list[dict[str, Any]] = Field(default_factory=list)
    personal_memory: dict[str, Any] = Field(default_factory=dict)
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
    scopes: set[str] = {"today", "tasks", "schedule", "goals", "memory"}

    strategic_hints = (
        "apprendre",
        "continuer",
        "reprendre",
        "suspendre",
        "pause",
        "formation",
        "nouvelle compétence",
        "compétence",
        "idée",
        "projet",
        "objectif",
        "objectifs",
        "python",
        "react",
        "programme",
        "réorganise",
        "réorganiser",
        "disponibilité",
        "disponibilités",
        "heures",
        "examen",
        "partiel",
        "activité",
        "approfondir",
        "maîtriser",
        "suivi",
        "manquée",
        "manqué",
        "raté",
        "ajuster",
    )
    if any(word in lowered for word in strategic_hints):
        scopes.update({"learning", "skills", "projects", "schedule", "goals", "memory"})

    if any(
        word in lowered
        for word in (
            "parcours",
            "module",
            "leçon",
            "apprendre",
            "exercice",
            "cours",
            "notion",
            "réviser",
            "révision",
            "programme",
            "demain",
            "journée",
        )
    ):
        scopes.add("learning")
    if any(
        word in lowered
        for word in (
            "compétence",
            "preuve",
            "niveau",
            "maîtrise",
            "évaluer",
            "évaluation",
            "test",
            "quiz",
            "lacune",
            "renforcer",
            "réviser",
            "révision",
            "programme",
            "demain",
            "journée",
        )
    ):
        scopes.add("skills")
    if any(
        word in lowered
        for word in (
            "projet",
            "livrable",
            "prochaine action",
            "dispersion",
            "devoir",
            "programme",
            "demain",
            "pause",
            "suspendre",
        )
    ):
        scopes.add("projects")
    if any(word in lowered for word in ("bilan", "hebdo", "semaine", "séance", "temps", "progression")):
        scopes.update({"weekly", "schedule", "projects", "learning", "skills"})

    return scopes


def is_university_course_event(event: ScheduleEventRecord) -> bool:
    return (
        event.type == ScheduleEventType.course
        or event.source == ScheduleEventSource.timetable_import
    )


def _parse_hhmm_to_time(hhmm: str | None, fallback: time) -> time:
    if not hhmm:
        return fallback
    parts = str(hhmm).strip().split(":")
    try:
        h = max(0, min(23, int(parts[0])))
        m = max(0, min(59, int(parts[1]))) if len(parts) > 1 else 0
        return time(h, m)
    except (ValueError, IndexError):
        return fallback


def compute_day_availability_plan(
    *,
    day_date: date,
    all_events: list[ScheduleEventRecord],
    tz: ZoneInfo,
    now_utc: datetime,
    study_start_hour: int = 8,
    study_end_hour: int = 21,
    excluded_days: set[int] | None = None,
    availability_rules: list[Any] | None = None,
) -> dict[str, Any]:
    """
    Calcule pour une journée donnée :
    - Les cours universitaires (verrouillés)
    - Les séances personnelles déjà planifiées et indisponibilités / pauses
    - Les périodes libres réelles (en respectant une pause de 20 min autour des cours et la pause déjeuner 12:30-13:30)
    - Jusqu'à 3 créneaux de travail recommandés (60 à 90 min max chacun) en privilégiant les disponibilités confirmées.
    """
    window_start = datetime.combine(day_date, time(study_start_hour, 0), tzinfo=tz)
    window_end = datetime.combine(
        day_date,
        time(study_end_hour, 30 if study_end_hour < 23 else 0),
        tzinfo=tz,
    )
    is_excluded_day = day_date.weekday() in (excluded_days or set())

    local_now = now_utc.astimezone(tz)
    if day_date == local_now.date() and local_now > window_start:
        # Arrondir au prochain quart d'heure ou heure pleine (+15 min de marge)
        rounded_min = ((local_now.minute // 15) + 1) * 15
        if rounded_min >= 60:
            candidate_start = (local_now + timedelta(hours=1)).replace(
                minute=0, second=0, microsecond=0
            )
        else:
            candidate_start = local_now.replace(
                minute=rounded_min, second=0, microsecond=0
            )
        if candidate_start > window_start:
            window_start = candidate_start

    day_events = [
        ev
        for ev in all_events
        if ev.starts_at.astimezone(tz).date() == day_date
        or ev.ends_at.astimezone(tz).date() == day_date
    ]
    day_events.sort(key=lambda e: e.starts_at)

    uni_courses: list[dict[str, Any]] = []
    personal_blocks: list[dict[str, Any]] = []
    confirmed_availabilities: list[dict[str, Any]] = []
    busy_intervals: list[tuple[datetime, datetime]] = []

    # Pause déjeuner préservée par défaut (12:30 - 13:30)
    lunch_start = datetime.combine(day_date, time(12, 30), tzinfo=tz)
    lunch_end = datetime.combine(day_date, time(13, 30), tzinfo=tz)
    busy_intervals.append((lunch_start, lunch_end))

    for rule in availability_rules or []:
        if not getattr(rule, "active", getattr(rule, "is_active", True)):
            continue
        r_dow = getattr(rule, "day_of_week", None)
        r_spec = getattr(rule, "specific_date", None)
        if r_spec is not None and r_spec != day_date:
            continue
        if r_spec is None and r_dow is not None and int(r_dow) != day_date.weekday():
            continue
        r_type_raw = getattr(rule, "rule_type", "")
        r_type = r_type_raw.value if hasattr(r_type_raw, "value") else str(r_type_raw)
        t_start = _parse_hhmm_to_time(getattr(rule, "start_time", "09:00"), time(9, 0))
        t_end = _parse_hhmm_to_time(getattr(rule, "end_time", "10:30"), time(10, 30))
        dt_start = datetime.combine(day_date, t_start, tzinfo=tz)
        dt_end = datetime.combine(day_date, t_end, tzinfo=tz)
        if dt_end <= dt_start:
            continue
        rule_item = {
            "id": str(getattr(rule, "id", "")),
            "title": getattr(rule, "label", None) or getattr(rule, "title", "Règle de disponibilité"),
            "rule_type": r_type,
            "local_start_time": dt_start.strftime("%H:%M"),
            "local_end_time": dt_end.strftime("%H:%M"),
            "starts_at": dt_start.astimezone(timezone.utc).isoformat(),
            "ends_at": dt_end.astimezone(timezone.utc).isoformat(),
        }
        if r_type in ("personal_unavailability", "recovery_time"):
            personal_blocks.append(rule_item)
            busy_intervals.append((dt_start, dt_end))
        elif r_type == "confirmed_availability":
            confirmed_availabilities.append(rule_item)

    for ev in day_events:
        ev_start_local = ev.starts_at.astimezone(tz)
        ev_end_local = ev.ends_at.astimezone(tz)
        item = {
            "id": str(ev.id),
            "title": ev.title,
            "type": ev.type.value,
            "source": ev.source.value,
            "session_subtype": ev.session_subtype,
            "teacher": ev.teacher,
            "room": ev.room,
            "group_name": ev.group_name,
            "starts_at": ev.starts_at.isoformat(),
            "ends_at": ev.ends_at.isoformat(),
            "local_start_time": ev_start_local.strftime("%H:%M"),
            "local_end_time": ev_end_local.strftime("%H:%M"),
        }
        if is_university_course_event(ev):
            uni_courses.append(item)
            # Pause tampon de 15 min avant et 20 min après chaque cours universitaire
            busy_intervals.append(
                (ev_start_local - timedelta(minutes=15), ev_end_local + timedelta(minutes=20))
            )
        else:
            personal_blocks.append(item)
            busy_intervals.append(
                (ev_start_local - timedelta(minutes=10), ev_end_local + timedelta(minutes=15))
            )

    busy_intervals.sort(key=lambda pair: pair[0])
    merged_busy: list[tuple[datetime, datetime]] = []
    for b_start, b_end in busy_intervals:
        if not merged_busy or b_start > merged_busy[-1][1]:
            merged_busy.append((b_start, b_end))
        else:
            merged_busy[-1] = (merged_busy[-1][0], max(merged_busy[-1][1], b_end))

    free_periods: list[dict[str, Any]] = []
    cursor = window_start
    if cursor < window_end:
        for b_start, b_end in merged_busy:
            if b_end <= cursor:
                continue
            if b_start > cursor:
                gap_end = min(b_start, window_end)
                gap_minutes = round((gap_end - cursor).total_seconds() / 60)
                if gap_minutes >= 45:
                    free_periods.append(
                        {
                            "local_start_time": cursor.strftime("%H:%M"),
                            "local_end_time": gap_end.strftime("%H:%M"),
                            "starts_at": cursor.astimezone(timezone.utc).isoformat(),
                            "ends_at": gap_end.astimezone(timezone.utc).isoformat(),
                            "duration_minutes": gap_minutes,
                        }
                    )
            cursor = max(cursor, b_end)
            if cursor >= window_end:
                break

        if cursor < window_end:
            gap_minutes = round((window_end - cursor).total_seconds() / 60)
            if gap_minutes >= 45:
                free_periods.append(
                    {
                        "local_start_time": cursor.strftime("%H:%M"),
                        "local_end_time": window_end.strftime("%H:%M"),
                        "starts_at": cursor.astimezone(timezone.utc).isoformat(),
                        "ends_at": window_end.astimezone(timezone.utc).isoformat(),
                        "duration_minutes": gap_minutes,
                    }
                )

    # Sélection raisonnée de créneaux de travail recommandés (max 3 blocs de 60 à 90 min, avec pauses)
    recommended_windows: list[dict[str, Any]] = []
    for period in free_periods:
        if len(recommended_windows) >= 3:
            break
        p_start = datetime.fromisoformat(period["starts_at"]).astimezone(tz)
        p_end = datetime.fromisoformat(period["ends_at"]).astimezone(tz)
        avail_min = round((p_end - p_start).total_seconds() / 60)

        block_min = 90 if avail_min >= 105 else 60
        if avail_min < 60:
            block_min = avail_min
        slot_end = p_start + timedelta(minutes=block_min)
        recommended_windows.append(
            {
                "local_start_time": p_start.strftime("%H:%M"),
                "local_end_time": slot_end.strftime("%H:%M"),
                "starts_at": p_start.astimezone(timezone.utc).isoformat(),
                "ends_at": slot_end.astimezone(timezone.utc).isoformat(),
                "duration_minutes": block_min,
            }
        )
        # Si la période libre est très longue (>= 3h30) et qu'on a encore de la place, proposer un second bloc après 30 min de pause
        second_start = slot_end + timedelta(minutes=30)
        if len(recommended_windows) < 3 and round((p_end - second_start).total_seconds() / 60) >= 60:
            second_end = second_start + timedelta(minutes=60)
            recommended_windows.append(
                {
                    "local_start_time": second_start.strftime("%H:%M"),
                    "local_end_time": second_end.strftime("%H:%M"),
                    "starts_at": second_start.astimezone(timezone.utc).isoformat(),
                    "ends_at": second_end.astimezone(timezone.utc).isoformat(),
                    "duration_minutes": 60,
                }
            )

    if is_excluded_day:
        free_periods = []
        recommended_windows = []

    return {
        "date": day_date.isoformat(),
        "is_excluded_day": is_excluded_day,
        "university_courses": uni_courses,
        "personal_blocks": personal_blocks,
        "confirmed_availabilities": confirmed_availabilities,
        "free_periods": free_periods,
        "recommended_study_windows": recommended_windows,
        "pause_policy": "Pause déjeuner (12:30 à 13:30) et marges de récupération (15 à 20 min autour des cours) préservées.",
    }


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
        course_repo: SqlCourseRepository | None = None,
        goal_repo: Any | None = None,
        ai_memory_repo: SqlAiMemoryRepository | None = None,
        planning_repo: Any | None = None,
    ) -> None:
        self._profile_service = profile_service
        self._task_repo = task_repo
        self._schedule_repo = schedule_repo
        self._session_repo = session_repo
        self._learning_repo = learning_repo
        self._skill_repo = skill_repo
        self._project_repo = project_repo
        self._course_repo = course_repo
        self._goal_repo = goal_repo
        self._ai_memory_repo = ai_memory_repo
        self._planning_repo = planning_repo

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
        memory_record = self._ai_memory_repo.get(user_id) if self._ai_memory_repo is not None else None
        tz = ZoneInfo(profile.timezone)
        local_now = ref_now.astimezone(tz)
        today_date = local_now.date()
        tomorrow_date = today_date + timedelta(days=1)
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
                "project_id": str(t.project_id) if t.project_id else None,
                "is_overdue": is_task_overdue(t, profile.timezone, ref_now),
            }
            for t in active_tasks[:MAX_CONTEXT_TASKS]
        ]

        schedule_payload: list[dict[str, Any]] = []
        university_courses_payload: list[dict[str, Any]] = []
        availability_payload: dict[str, Any] = {}
        all_events: list[ScheduleEventRecord] = []
        weekly_candidate_slots: list[dict[str, Any]] = []
        multi_week_candidate_slots: list[dict[str, Any]] = []
        weekly_scheduled_minutes = 0
        weekly_course_minutes = 0
        weekly_personal_minutes = 0

        avail_prefs = _parse_availability_preferences(profile.preferences, memory_record)
        study_start_hour = int(avail_prefs["study_start_hour"])
        study_end_hour = int(avail_prefs["study_end_hour"])
        max_daily_study_minutes = int(avail_prefs["max_daily_study_minutes"])
        excluded_days_set = set(avail_prefs["excluded_days"])
        availability_rules: list[Any] = (
            self._planning_repo.list_availability_rules(user_id, active_only=True)
            if self._planning_repo is not None
            else []
        )
        rules_payload = [
            {
                "id": str(r.id),
                "rule_type": r.rule_type.value if hasattr(r.rule_type, "value") else str(r.rule_type),
                "title": getattr(r, "label", None) or getattr(r, "title", "Règle"),
                "day_of_week": r.day_of_week,
                "specific_date": r.specific_date.isoformat() if getattr(r, "specific_date", None) else None,
                "start_time": r.start_time,
                "end_time": r.end_time,
                "preference_weight": getattr(r, "preference_weight", 1),
            }
            for r in availability_rules[:30]
        ]

        all_events = self._schedule_repo.list_by_user(user_id)
        relevant_events = [
            e
            for e in all_events
            if e.ends_at >= ref_now - timedelta(hours=24)
            and e.starts_at <= ref_now + timedelta(days=21)
        ]
        relevant_events.sort(key=lambda item: item.starts_at)
        if not relevant_events and ("schedule" in scopes or "today" in scopes or "weekly" in scopes):
            missing_data.append("Aucun créneau planifié sur la période.")

        for e in relevant_events[:MAX_CONTEXT_EVENTS]:
            local_s = e.starts_at.astimezone(tz)
            local_e = e.ends_at.astimezone(tz)
            is_uni = is_university_course_event(e)
            ev_dict = {
                "id": str(e.id),
                "title": e.title,
                "type": e.type.value,
                "source": e.source.value,
                "is_university_course": is_uni,
                "session_subtype": e.session_subtype,
                "teacher": e.teacher,
                "room": e.room,
                "group_name": e.group_name,
                "starts_at": e.starts_at.isoformat(),
                "ends_at": e.ends_at.isoformat(),
                "local_date": local_s.date().isoformat(),
                "local_start_time": local_s.strftime("%H:%M"),
                "local_end_time": local_e.strftime("%H:%M"),
                "is_today": local_s.date() == today_date or local_e.date() == today_date,
                "is_tomorrow": local_s.date() == tomorrow_date,
            }
            schedule_payload.append(ev_dict)
            if is_uni:
                university_courses_payload.append(ev_dict)

        today_plan = compute_day_availability_plan(
            day_date=today_date,
            all_events=all_events,
            tz=tz,
            now_utc=ref_now,
            study_start_hour=study_start_hour,
            study_end_hour=study_end_hour,
            excluded_days=excluded_days_set,
            availability_rules=availability_rules,
        )
        tomorrow_plan = compute_day_availability_plan(
            day_date=tomorrow_date,
            all_events=all_events,
            tz=tz,
            now_utc=ref_now,
            study_start_hour=study_start_hour,
            study_end_hour=study_end_hour,
            excluded_days=excluded_days_set,
            availability_rules=availability_rules,
        )

        days_summary: list[dict[str, Any]] = []
        for offset in range(21):
            day_date = today_date + timedelta(days=offset)
            day_start_utc = datetime.combine(day_date, time(0, 0), tzinfo=tz).astimezone(
                timezone.utc
            )
            day_end_utc = day_start_utc + timedelta(days=1)
            day_events_list = [
                ev
                for ev in all_events
                if ev.ends_at > day_start_utc and ev.starts_at < day_end_utc
            ]
            day_minutes = 0
            for ev in day_events_list:
                clipped_start = max(ev.starts_at, day_start_utc)
                clipped_end = min(ev.ends_at, day_end_utc)
                dur_min = max(0, round((clipped_end - clipped_start).total_seconds() / 60))
                day_minutes += dur_min
                if offset < 7:
                    weekly_scheduled_minutes += dur_min
                    if is_university_course_event(ev):
                        weekly_course_minutes += dur_min
                    else:
                        weekly_personal_minutes += dur_min

            day_plan = (
                today_plan
                if offset == 0
                else (
                    tomorrow_plan
                    if offset == 1
                    else compute_day_availability_plan(
                        day_date=day_date,
                        all_events=all_events,
                        tz=tz,
                        now_utc=ref_now,
                        study_start_hour=study_start_hour,
                        study_end_hour=study_end_hour,
                        excluded_days=excluded_days_set,
                        availability_rules=availability_rules,
                    )
                )
            )
            rec_windows = day_plan.get("recommended_study_windows") or []
            if day_minutes >= max_daily_study_minutes:
                allowed_windows: list[dict[str, Any]] = []
            elif day_minutes >= round(max_daily_study_minutes * 0.7):
                allowed_windows = rec_windows[:1]
            else:
                allowed_windows = rec_windows

            day_idx = day_date.weekday()
            day_name = DAY_NAMES_FR[day_idx]
            for win in allowed_windows:
                slot_item = {
                    "day_of_week": day_idx,
                    "day_label": day_name,
                    "local_date": day_date.isoformat(),
                    "week_index": offset // 7,
                    "local_start_time": win["local_start_time"],
                    "local_end_time": win["local_end_time"],
                    "starts_at": win["starts_at"],
                    "ends_at": win["ends_at"],
                    "duration_minutes": win["duration_minutes"],
                }
                multi_week_candidate_slots.append(slot_item)
                if offset < 7:
                    weekly_candidate_slots.append(slot_item)

            if offset < 7:
                days_summary.append(
                    {
                        "date": day_date.isoformat(),
                        "day_label": day_name,
                        "scheduled_minutes": day_minutes,
                        "university_courses_count": len(
                            day_plan.get("university_courses") or []
                        ),
                        "candidate_slots_count": len(allowed_windows),
                    }
                )

        availability_payload = {
            "preferences": avail_prefs,
            "rules": rules_payload,
            "today": today_plan,
            "tomorrow": tomorrow_plan,
            "weekly_candidate_slots": weekly_candidate_slots,
            "multi_week_candidate_slots": multi_week_candidate_slots,
            "days_summary": days_summary,
        }

        learning_payload: dict[str, Any] = {}
        courses_payload: list[dict[str, Any]] = []
        active_learning_paths_count = 0
        if self._course_repo is not None:
            user_courses = self._course_repo.list_courses(user_id)
            user_courses.sort(
                key=lambda c: (0 if c.status.value == "active" else 1, c.updated_at),
            )
            all_course_lessons = self._course_repo.list_lessons(user_id)
            lessons_by_course: dict[UUID, list[Any]] = {}
            for l in all_course_lessons:
                lessons_by_course.setdefault(l.course_id, []).append(l)

            for c in user_courses[:MAX_CONTEXT_COURSES]:
                c_lessons = sorted(
                    lessons_by_course.get(c.id, []),
                    key=lambda item: item.position,
                )
                done_cnt = sum(1 for item in c_lessons if item.status.value == "completed")
                next_incomplete = next(
                    (
                        {"id": str(item.id), "title": item.title, "position": item.position}
                        for item in c_lessons
                        if item.status.value != "completed"
                    ),
                    None,
                )
                courses_payload.append(
                    {
                        "id": str(c.id),
                        "title": c.title,
                        "subject": c.subject,
                        "current_level": c.current_level,
                        "total_levels": c.total_levels,
                        "status": c.status.value,
                        "completed_lessons_count": done_cnt,
                        "total_lessons_count": len(c_lessons),
                        "next_incomplete_lesson": next_incomplete,
                    }
                )
        paths = self._learning_repo.list_paths(user_id)
        modules = self._learning_repo.list_modules(user_id)
        lessons = self._learning_repo.list_lessons(user_id)
        if not paths and "learning" in scopes and not courses_payload:
            missing_data.append("Aucun parcours d’apprentissage enregistré.")
        completed_lessons = sum(1 for l in lessons if l.status.value == "completed")
        active_learning_paths_count = sum(
            1 for p in paths if p.status == LearningStatus.active
        )
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
        approved_assessments_count = 0
        pending_assessments_count = 0
        needs_reinforcement_count = 0
        skills = self._skill_repo.list_skills(user_id)
        evidence = self._skill_repo.list_evidence(user_id)
        assessments = self._skill_repo.list_assessments(user_id)
        ev_count_by_skill: dict[UUID, int] = {}
        for ev in evidence:
            ev_count_by_skill[ev.skill_id] = ev_count_by_skill.get(ev.skill_id, 0) + 1
        assessments_by_skill: dict[UUID, list[Any]] = {}
        for item in assessments:
            assessments_by_skill.setdefault(item.skill_id, []).append(item)
            if item.status.value == "approved":
                approved_assessments_count += 1
            elif item.status.value in ("pending", "submitted", "evaluated"):
                pending_assessments_count += 1
            if item.status.value == "rejected" or item.passed is False:
                needs_reinforcement_count += 1
        for items in assessments_by_skill.values():
            items.sort(key=lambda a: a.created_at, reverse=True)

        if not skills and "skills" in scopes:
            missing_data.append("Aucune compétence enregistrée.")
        for s in skills[:MAX_CONTEXT_SKILLS]:
            skill_assessments = assessments_by_skill.get(s.id, [])
            latest = skill_assessments[0] if skill_assessments else None
            skills_payload.append(
                {
                    "id": str(s.id),
                    "name": s.name,
                    "domain": s.domain,
                    "current_level": s.current_level,
                    "target_level": s.target_level,
                    "evidence_count": ev_count_by_skill.get(s.id, 0),
                    "assessments_count": len(skill_assessments),
                    "latest_assessment_id": str(latest.id) if latest else None,
                    "latest_assessment_status": latest.status.value if latest else None,
                    "latest_assessment_passed": latest.passed if latest else None,
                    "latest_assessment_score": latest.score if latest else None,
                    "latest_assessment_proposed_level": (
                        latest.proposed_level if latest else None
                    ),
                    "latest_assessment_evidence_ids": (
                        list(latest.evidence_ids) if latest else []
                    ),
                    "latest_gaps": list(latest.gaps_identified) if latest else [],
                }
            )

        projects_payload: list[dict[str, Any]] = []
        active_projects_count = 0
        projects = self._project_repo.list_projects(user_id)
        if not projects and "projects" in scopes:
            missing_data.append("Aucun projet enregistré.")
        status_order = {
            ProjectStatus.active: 0,
            ProjectStatus.paused: 1,
            ProjectStatus.planned: 2,
            ProjectStatus.blocked: 3,
            ProjectStatus.completed: 4,
            ProjectStatus.archived: 5,
        }
        projects.sort(key=lambda p: (status_order.get(p.status, 9), p.updated_at))
        active_projects_count = sum(1 for p in projects if p.status == ProjectStatus.active)
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

        personal_goals_payload: list[dict[str, Any]] = []
        if self._goal_repo is not None:
            raw_goals = self._goal_repo.list_goals(user_id)
            raw_goals.sort(
                key=lambda g: (
                    0 if getattr(g, "is_primary", False) else 1,
                    0 if g.status.value == "active" else 1,
                    -g.created_at.timestamp(),
                )
            )
            for g in raw_goals[:10]:
                history = list(getattr(g, "progress_history", None) or [])
                personal_goals_payload.append(
                    {
                        "id": str(g.id),
                        "title": g.title,
                        "category": g.category.value,
                        "goal": g.goal,
                        "current_level": g.current_level,
                        "target_level": g.target_level,
                        "priority": g.priority.value,
                        "is_primary": bool(getattr(g, "is_primary", False)),
                        "status": g.status.value,
                        "weekly_target_minutes": g.weekly_target_minutes,
                        "next_action": g.next_action,
                        "target_date": g.target_date.isoformat() if g.target_date else None,
                        "skill_id": str(g.skill_id) if g.skill_id else None,
                        "learning_path_id": str(g.learning_path_id) if g.learning_path_id else None,
                        "course_id": str(g.course_id) if g.course_id else None,
                        "latest_progress": history[-1] if history else None,
                    }
                )

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
                "planned_activity": getattr(s, "planned_activity", None),
                "actual_activity": getattr(s, "actual_activity", None),
                "outcome_status": getattr(s, "outcome_status", None),
                "deliverable_summary": getattr(s, "deliverable_summary", None),
                "blockers": getattr(s, "blockers", None),
                "started_at": s.started_at.isoformat(),
            }
            for s in sorted(completed_sessions_7d, key=lambda item: item.started_at, reverse=True)[
                :MAX_CONTEXT_SESSIONS
            ]
        ]

        # Suivi des activités acceptées mais non réalisées sur les 7 derniers jours (chaque session couvre au plus 1 bloc)
        past_study_blocks = [
            ev
            for ev in all_events
            if ev.ends_at < ref_now
            and ev.starts_at >= week_ago_utc
            and ev.type in (ScheduleEventType.learning, ScheduleEventType.project)
        ]
        used_session_ids: set[UUID] = set()
        missed_block_titles: list[str] = []
        for ev in sorted(past_study_blocks, key=lambda item: item.starts_at, reverse=True):
            ev_date = ev.starts_at.astimezone(tz).date()
            ev_title_lower = ev.title.strip().lower()
            matched_session = None
            for s in completed_sessions_7d:
                if s.id in used_session_ids:
                    continue
                st = s.title.strip().lower()
                s_date = s.started_at.astimezone(tz).date()
                title_match = bool(st and (ev_title_lower in st or st in ev_title_lower))
                time_overlap = (
                    s.started_at <= ev.ends_at + timedelta(hours=2)
                    and (s.ended_at or s.started_at) >= ev.starts_at - timedelta(hours=2)
                )
                if title_match or time_overlap or s_date == ev_date:
                    matched_session = s
                    break
            if matched_session is not None:
                used_session_ids.add(matched_session.id)
            else:
                missed_block_titles.append(ev.title)

        missed_study_blocks_count = len(missed_block_titles)
        critical_tasks_count = sum(
            1 for t in active_tasks if t.priority == TaskPriority.critical
        )
        strategic_analysis_payload = {
            "active_priority_title": profile.active_priority_title,
            "active_priority_task_id": (
                str(profile.active_priority_task_id) if profile.active_priority_task_id else None
            ),
            "active_priority_project_id": (
                str(profile.active_priority_project_id) if profile.active_priority_project_id else None
            ),
            "critical_tasks_count": critical_tasks_count,
            "overdue_tasks_count": len(overdue_tasks),
            "active_learning_paths_count": active_learning_paths_count,
            "active_projects_count": active_projects_count,
            "weekly_scheduled_minutes": weekly_scheduled_minutes,
            "weekly_course_minutes": weekly_course_minutes,
            "weekly_personal_minutes": weekly_personal_minutes,
            "available_weekly_slots_count": len(weekly_candidate_slots),
            "past_scheduled_study_blocks_count": len(past_study_blocks),
            "completed_study_sessions_count": len(completed_sessions_7d),
            "missed_study_blocks_count": missed_study_blocks_count,
            "missed_block_titles": missed_block_titles[:5],
            "needs_schedule_readjustment": missed_study_blocks_count >= 2,
        }

        personal_memory_payload: dict[str, Any] = {}
        if memory_record is not None:
            personal_memory_payload = {
                "academic_context": dict(memory_record.academic_context or {}),
                "availability_preferences": dict(memory_record.availability_preferences or {}),
                "learning_preferences": dict(memory_record.learning_preferences or {}),
                "constraints": list(memory_record.constraints or []),
                "long_term_goals": list(memory_record.long_term_goals or []),
                "weekly_study_hours": memory_record.weekly_study_hours,
                "default_session_minutes": memory_record.default_session_minutes,
                "auto_execute_simple_actions": memory_record.auto_execute_simple_actions,
                "recent_decisions": list(memory_record.recent_decisions or [])[:6],
                "execution_history": list(memory_record.execution_history or [])[:6],
            }

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
            university_courses=university_courses_payload,
            availability=availability_payload,
            strategic_analysis=strategic_analysis_payload,
            learning=learning_payload,
            courses=courses_payload,
            skills=skills_payload,
            projects=projects_payload,
            personal_goals=personal_goals_payload,
            personal_memory=personal_memory_payload,
            recent_sessions=recent_sessions_payload,
            stats={
                "active_tasks_count": len(active_tasks),
                "critical_tasks_count": critical_tasks_count,
                "overdue_tasks_count": len(overdue_tasks),
                "done_tasks_last_7d_count": len(done_last_7d),
                "completed_sessions_last_7d_count": len(completed_sessions_7d),
                "completed_minutes_last_7d": total_minutes_7d,
                "approved_assessments_count": approved_assessments_count,
                "pending_assessments_count": pending_assessments_count,
                "needs_reinforcement_count": needs_reinforcement_count,
                "university_courses_count": len(university_courses_payload),
                "weekly_scheduled_minutes": weekly_scheduled_minutes,
                "available_weekly_slots_count": len(weekly_candidate_slots),
                "missed_study_blocks_count": missed_study_blocks_count,
            },
            missing_data=missing_data,
            is_partial_data=len(missing_data) > 0,
        )
