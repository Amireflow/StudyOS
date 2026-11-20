from datetime import date, datetime, time, timedelta, timezone
import re
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo
from app.core.errors import AppError
from app.repositories.courses_sql import SqlCourseRepository
from app.repositories.learning_sql import (
    LearningModuleRecord,
    LearningPathRecord,
    LessonRecord,
    PersonalGoalRecord,
    ProjectRecord,
    SkillRecord,
    SqlLearningRepository,
    SqlPersonalGoalRepository,
    SqlProjectRepository,
    SqlSkillRepository,
)
from app.repositories.memory import (
    ProfileRepository,
    ScheduleEventRecord,
    ScheduleRepository,
    SessionRepository,
    TaskRecord,
    TaskRepository,
)
from app.schemas.common import (
    LearningStatus,
    ObjectiveCategory,
    ObjectiveStatus,
    ProjectStatus,
    ScheduleEventSource,
    ScheduleEventType,
    SessionStatus,
    TaskPriority,
    TaskSource,
    TaskStatus,
)
from app.schemas.objectives import (
    ConfirmIntakeRequest,
    ConfirmIntakeResponse,
    ConversationalIntakeRequest,
    ConversationalIntakeResponse,
    ExtractedObjectiveCandidate,
    ObjectivesOverviewResponse,
    PersonalGoalCreate,
    PersonalGoalResponse,
    PersonalGoalUpdate,
    UnifiedPlanAdaptationItem,
    UnifiedPlanApplyRequest,
    UnifiedPlanApplyResponse,
    UnifiedPlanGenerateRequest,
    UnifiedPlanResponse,
    UnifiedPlanSlot,
)
from app.schemas.projects import ProjectCreate
from app.ai.context_builder import _parse_availability_preferences
from app.services.projects_service import ProjectService
from app.services.schedule_service import do_events_overlap
from app.services.sessions_service import compute_session_duration_minutes

DAY_LABELS_FR: tuple[str, ...] = (
    "Lundi",
    "Mardi",
    "Mercredi",
    "Jeudi",
    "Vendredi",
    "Samedi",
    "Dimanche",
)

KNOWN_TECH_TOPICS: tuple[tuple[str, str, ObjectiveCategory, str], ...] = (
    ("python", "Python", ObjectiveCategory.language, "Backend & Data"),
    ("react", "React", ObjectiveCategory.framework, "Frontend & Web"),
    ("typescript", "TypeScript", ObjectiveCategory.language, "Frontend & Web"),
    ("javascript", "JavaScript", ObjectiveCategory.language, "Frontend & Web"),
    ("développement web", "Développement Web", ObjectiveCategory.technology, "Web Fullstack"),
    ("developpement web", "Développement Web", ObjectiveCategory.technology, "Web Fullstack"),
    ("sql", "SQL & Bases de données", ObjectiveCategory.technology, "Data & Backend"),
    ("postgresql", "PostgreSQL", ObjectiveCategory.technology, "Data & Backend"),
    ("fastapi", "FastAPI", ObjectiveCategory.framework, "Backend & API"),
    ("rust", "Rust", ObjectiveCategory.language, "Systèmes"),
    ("java", "Java", ObjectiveCategory.language, "Backend & POO"),
    ("docker", "Docker", ObjectiveCategory.technology, "DevOps & Cloud"),
    ("anglais", "Anglais technique", ObjectiveCategory.spoken_language, "Langues"),
)


def _is_academic_fixed_event(ev: ScheduleEventRecord) -> bool:
    return (
        ev.source == ScheduleEventSource.timetable_import
        or ev.import_id is not None
        or ev.type == ScheduleEventType.course
    )


class ObjectivesService:
    """Gère les objectifs personnels hors emploi du temps, la collecte conversationnelle et le moteur de planification unifié."""

    def __init__(
        self,
        *,
        goal_repo: SqlPersonalGoalRepository,
        project_repo: SqlProjectRepository,
        project_service: ProjectService,
        learning_repo: SqlLearningRepository,
        skill_repo: SqlSkillRepository,
        course_repo: SqlCourseRepository | None,
        task_repo: TaskRepository,
        schedule_repo: ScheduleRepository,
        session_repo: SessionRepository,
        profile_repo: ProfileRepository,
    ) -> None:
        self._goal_repo = goal_repo
        self._project_repo = project_repo
        self._project_service = project_service
        self._learning_repo = learning_repo
        self._skill_repo = skill_repo
        self._course_repo = course_repo
        self._task_repo = task_repo
        self._schedule_repo = schedule_repo
        self._session_repo = session_repo
        self._profile_repo = profile_repo

    def _enrich_goal_response(
        self,
        user_id: UUID,
        record: PersonalGoalRecord,
        *,
        all_sessions: list[Any] | None = None,
        now_utc: datetime | None = None,
    ) -> PersonalGoalResponse:
        ref_now = now_utc or datetime.now(timezone.utc)
        seven_days_ago = ref_now - timedelta(days=7)
        sessions = (
            all_sessions
            if all_sessions is not None
            else self._session_repo.list_by_user(user_id)
        )

        goal_sessions = [
            s
            for s in sessions
            if s.status == SessionStatus.completed
            and s.ended_at is not None
            and (
                getattr(s, "goal_id", None) == record.id
                or (record.skill_id is not None and s.skill_id == record.skill_id)
                or record.title.lower() in s.title.lower()
            )
        ]
        recent_minutes = sum(
            compute_session_duration_minutes(s, ref_now)
            for s in goal_sessions
            if s.started_at >= seven_days_ago
        )

        # Synchroniser le niveau actuel avec la compétence liée si elle existe
        effective_current_level = record.current_level
        if record.skill_id is not None:
            linked_skill = self._skill_repo.get_skill(user_id, record.skill_id)
            if linked_skill is not None:
                effective_current_level = linked_skill.current_level

        # Section 8 : Ne jamais considérer un objectif comme accompli uniquement parce que sa date est arrivée
        is_behind = False
        delay_reason: str | None = None
        if record.status == ObjectiveStatus.active:
            if record.target_date is not None and record.target_date <= ref_now:
                is_behind = True
                delay_reason = (
                    "Échéance atteinte sans validation complète des critères de réussite "
                    "(un objectif n’est jamais marqué accompli uniquement par sa date)."
                )
            elif (
                record.weekly_target_minutes > 0
                and (ref_now - record.created_at).total_seconds() >= 3 * 86400
                and recent_minutes < record.weekly_target_minutes // 2
            ):
                is_behind = True
                delay_reason = (
                    f"Volume hebdomadaire réalisé ({recent_minutes} min) inférieur à l’objectif "
                    f"souhaité ({record.weekly_target_minutes} min/sem.)."
                )
            # Vérifier si la dernière séance a signalé une difficulté
            if record.progress_history:
                last_entry = record.progress_history[-1]
                if last_entry.get("difficulties"):
                    is_behind = True
                    delay_reason = f"Difficulté signalée en séance : {last_entry['difficulties']}"

        data = record.model_dump()
        data["current_level"] = effective_current_level
        data["completed_minutes_last_7d"] = recent_minutes
        data["sessions_count"] = len(goal_sessions)
        data["is_behind_schedule"] = is_behind
        data["delay_reason"] = delay_reason
        return PersonalGoalResponse.model_validate(data)

    def list_goals(
        self,
        user_id: UUID,
        *,
        status_filter: ObjectiveStatus | None = None,
    ) -> list[PersonalGoalResponse]:
        records = self._goal_repo.list_goals(user_id)
        if status_filter is not None:
            records = [r for r in records if r.status == status_filter]
        sessions = self._session_repo.list_by_user(user_id)
        now = datetime.now(timezone.utc)
        records.sort(
            key=lambda item: (
                0 if item.is_primary else 1,
                0 if item.status == ObjectiveStatus.active else 1,
                -item.created_at.timestamp(),
            )
        )
        return [
            self._enrich_goal_response(user_id, item, all_sessions=sessions, now_utc=now)
            for item in records
        ]

    def get_goal(self, user_id: UUID, goal_id: UUID) -> PersonalGoalResponse:
        record = self._goal_repo.get(user_id, goal_id)
        if record is None:
            raise AppError(404, "NOT_FOUND", "Objectif personnel introuvable.")
        return self._enrich_goal_response(user_id, record)

    def create_goal(
        self,
        user_id: UUID,
        payload: PersonalGoalCreate,
    ) -> PersonalGoalResponse:
        now = datetime.now(timezone.utc)
        title = payload.title.strip()
        goal_text = (
            payload.goal.strip()
            if payload.goal and payload.goal.strip()
            else f"Maîtriser {title} et valider les acquis par des exercices et livrables vérifiables."
        )

        # Si l'utilisateur définit cet objectif comme priorité principale, désactiver is_primary sur les autres
        if payload.is_primary:
            for existing in self._goal_repo.list_goals(user_id):
                if existing.is_primary:
                    self._goal_repo.save(
                        existing.model_copy(update={"is_primary": False, "updated_at": now})
                    )
            profile = self._profile_repo.get(user_id)
            if profile is not None:
                self._profile_repo.save(
                    profile.model_copy(
                        update={
                            "active_priority_title": title,
                            "updated_at": now,
                        }
                    )
                )

        skill_id: UUID | None = None
        path_id: UUID | None = None
        course_id: UUID | None = None

        if payload.create_linked_entities:
            # 1. Relier ou créer la compétence correspondante (verrou pédagogique : démarre à 0 en base si nouvelle)
            existing_skills = self._skill_repo.list_skills(user_id)
            matched_skill = next(
                (s for s in existing_skills if s.name.lower() == title.lower()),
                None,
            )
            if matched_skill is None:
                matched_skill = self._skill_repo.save_skill(
                    SkillRecord(
                        id=uuid4(),
                        user_id=user_id,
                        name=title[:120],
                        domain="Objectif personnel",
                        description=payload.description or goal_text,
                        current_level=0,
                        target_level=payload.target_level or 3,
                        last_assessed_at=None,
                        created_at=now,
                        updated_at=now,
                    )
                )
            skill_id = matched_skill.id

            # 2. Relier ou créer le parcours pédagogique (LearningPath + Module + 2 Leçons)
            existing_paths = self._learning_repo.list_paths(user_id)
            matched_path = next(
                (p for p in existing_paths if title.lower() in p.title.lower()),
                None,
            )
            if matched_path is None:
                matched_path = self._learning_repo.save_path(
                    LearningPathRecord(
                        id=uuid4(),
                        user_id=user_id,
                        title=f"Parcours : {title}"[:140],
                        description=payload.description or goal_text,
                        status=LearningStatus.active,
                        goal=goal_text[:300],
                        created_at=now,
                        updated_at=now,
                    )
                )
                mod1 = self._learning_repo.save_module(
                    LearningModuleRecord(
                        id=uuid4(),
                        user_id=user_id,
                        path_id=matched_path.id,
                        title=f"Fondamentaux & pratique : {title}"[:140],
                        description=f"Progression structurée sur {title}",
                        position=1,
                        status=LearningStatus.active,
                        created_at=now,
                        updated_at=now,
                    )
                )
                self._learning_repo.save_lesson(
                    LessonRecord(
                        id=uuid4(),
                        user_id=user_id,
                        module_id=mod1.id,
                        title=f"Concepts clés et syntaxe de {title}"[:140],
                        content=f"Étudier les bases de {title} et réaliser un premier exercice guidé.",
                        resource_url=None,
                        position=1,
                        status=LearningStatus.active,
                        created_at=now,
                        updated_at=now,
                    )
                )
                self._learning_repo.save_lesson(
                    LessonRecord(
                        id=uuid4(),
                        user_id=user_id,
                        module_id=mod1.id,
                        title=f"Mise en pratique et mini-livrable {title}"[:140],
                        content=f"Construire un exercice concret sur {title} et soumettre le code.",
                        resource_url=None,
                        position=2,
                        status=LearningStatus.not_started,
                        created_at=now,
                        updated_at=now,
                    )
                )
            path_id = matched_path.id

            # 3. Relier un cours intelligent existant s'il porte sur le même sujet
            if self._course_repo is not None:
                courses = self._course_repo.list_courses(user_id)
                matched_course = next(
                    (
                        c
                        for c in courses
                        if title.lower() in c.subject.lower() or title.lower() in c.title.lower()
                    ),
                    None,
                )
                if matched_course is not None:
                    course_id = matched_course.id

        default_steps = payload.steps or [
            {"id": "step-1", "title": f"Assimiler les fondamentaux de {title}", "completed": False},
            {"id": "step-2", "title": f"Réussir une série d’exercices pratiques sur {title}", "completed": False},
            {"id": "step-3", "title": f"Livrer une preuve vérifiable et valider l’évaluation {title}", "completed": False},
        ]
        default_deliverables = payload.deliverables or [
            f"Exercices corrigés et code fonctionnel sur {title}",
        ]
        default_criteria = payload.success_criteria or [
            "Réussir une évaluation pratique vérifiée (verrou pédagogique)",
            "Fournir au moins une preuve concrète ou un livrable",
        ]
        default_next_action = (
            payload.next_action.strip()
            if payload.next_action and payload.next_action.strip()
            else f"Étudier le premier module de {title} et réaliser un exercice pratique"
        )

        record = PersonalGoalRecord(
            id=uuid4(),
            user_id=user_id,
            category=payload.category,
            title=title,
            description=payload.description,
            goal=goal_text,
            current_level=payload.current_level,
            target_level=payload.target_level,
            priority=payload.priority,
            is_primary=payload.is_primary,
            motivation=payload.motivation,
            start_date=payload.start_date or now,
            target_date=payload.target_date,
            weekly_target_minutes=payload.weekly_target_minutes,
            status=payload.status,
            steps=default_steps,
            deliverables=default_deliverables,
            next_action=default_next_action[:240],
            success_criteria=default_criteria,
            progress_history=[
                {
                    "timestamp": now.isoformat(),
                    "event": "created",
                    "summary": f"Objectif personnel « {title} » créé (hors emploi du temps universitaire).",
                }
            ],
            skill_id=skill_id,
            learning_path_id=path_id,
            course_id=course_id,
            created_at=now,
            updated_at=now,
        )
        saved = self._goal_repo.save(record)
        return self._enrich_goal_response(user_id, saved, now_utc=now)

    def update_goal(
        self,
        user_id: UUID,
        goal_id: UUID,
        payload: PersonalGoalUpdate,
    ) -> PersonalGoalResponse:
        existing = self._goal_repo.get(user_id, goal_id)
        if existing is None:
            raise AppError(404, "NOT_FOUND", "Objectif personnel introuvable.")

        now = datetime.now(timezone.utc)
        fields = payload.model_fields_set
        updates: dict[str, Any] = {"updated_at": now}

        for field_name in (
            "title",
            "category",
            "description",
            "goal",
            "current_level",
            "target_level",
            "priority",
            "is_primary",
            "motivation",
            "start_date",
            "target_date",
            "weekly_target_minutes",
            "status",
            "steps",
            "deliverables",
            "next_action",
            "success_criteria",
        ):
            if field_name in fields:
                val = getattr(payload, field_name)
                if field_name in ("title", "category", "goal", "priority", "status", "weekly_target_minutes") and val is None:
                    continue
                updates[field_name] = val

        if updates.get("is_primary") is True:
            for other in self._goal_repo.list_goals(user_id):
                if other.id != goal_id and other.is_primary:
                    self._goal_repo.save(
                        other.model_copy(update={"is_primary": False, "updated_at": now})
                    )
            profile = self._profile_repo.get(user_id)
            if profile is not None:
                self._profile_repo.save(
                    profile.model_copy(
                        update={
                            "active_priority_title": updates.get("title") or existing.title,
                            "updated_at": now,
                        }
                    )
                )

        if "status" in updates and updates["status"] != existing.status:
            history = list(existing.progress_history or [])
            history.append(
                {
                    "timestamp": now.isoformat(),
                    "event": "status_changed",
                    "summary": f"Statut changé de {existing.status.value} à {updates['status'].value}.",
                }
            )
            updates["progress_history"] = history

        saved = self._goal_repo.save(existing.model_copy(update=updates))
        return self._enrich_goal_response(user_id, saved, now_utc=now)

    def delete_goal(self, user_id: UUID, goal_id: UUID) -> None:
        if not self._goal_repo.delete(user_id, goal_id):
            raise AppError(404, "NOT_FOUND", "Objectif personnel introuvable.")

    def get_overview(self, user_id: UUID) -> ObjectivesOverviewResponse:
        """Section 1 : Sépare strictement les 3 sources de données (Obligations académiques, Objectifs personnels, Projets)."""
        all_events = self._schedule_repo.list_by_user(user_id)
        academic_events = [
            {
                "id": str(ev.id),
                "title": ev.title,
                "type": ev.type.value,
                "source": ev.source.value,
                "session_subtype": ev.session_subtype or "cours",
                "starts_at": ev.starts_at.isoformat(),
                "ends_at": ev.ends_at.isoformat(),
                "teacher": ev.teacher,
                "room": ev.room,
                "group_name": ev.group_name,
                "is_fixed_constraint": True,
            }
            for ev in sorted(all_events, key=lambda e: e.starts_at)
            if _is_academic_fixed_event(ev)
        ]

        goals = self.list_goals(user_id)
        projects = [p.model_dump(mode="json") for p in self._project_service.list_projects(user_id)]
        tasks = self._task_repo.list_by_user(user_id)
        profile = self._profile_repo.get(user_id)

        active_goals = [g for g in goals if g.status == ObjectiveStatus.active]
        primary_goal = next((g for g in active_goals if g.is_primary), None)
        secondary_goals = [g for g in active_goals if not g.is_primary]
        active_projects = [p for p in projects if p["status"] == ProjectStatus.active.value]
        critical_tasks = [
            t
            for t in tasks
            if t.status in (TaskStatus.todo, TaskStatus.in_progress)
            and t.priority == TaskPriority.critical
        ]

        primary_title = (
            (profile.active_priority_title if profile else None)
            or (primary_goal.title if primary_goal else None)
            or (active_projects[0]["name"] if active_projects else None)
            or (active_goals[0].title if active_goals else None)
        )

        return ObjectivesOverviewResponse(
            academic_obligations=academic_events,
            personal_goals=goals,
            projects=projects,
            priority_summary={
                "primary_priority_title": primary_title,
                "active_goals_count": len(active_goals),
                "secondary_goals_count": len(secondary_goals),
                "active_projects_count": len(active_projects),
                "max_active_priority_projects": 3,
                "critical_tasks_count": len(critical_tasks),
                "max_critical_tasks": 3,
                "anti_dispersion_respected": len(active_projects) <= 3 and len(critical_tasks) <= 3,
            },
        )

    def analyze_conversational_intake(
        self,
        user_id: UUID,
        payload: ConversationalIntakeRequest,
    ) -> ConversationalIntakeResponse:
        """Section 3 : Extrait les objectifs en langage naturel, identifie les manques sans rien inventer et pose des questions progressives."""
        prior_text = " ".join(
            m.get("content", "") for m in payload.history if m.get("role") == "user"
        )
        combined = f"{prior_text} {payload.message}".strip()
        lowered = combined.lower()
        known = payload.known_answers or {}

        existing_skills = {s.name.lower(): s for s in self._skill_repo.list_skills(user_id)}
        extracted: list[ExtractedObjectiveCandidate] = []
        seen_titles: set[str] = set()

        # 1. Détection des sujets technologiques et compétences connus
        for token, canonical_title, cat, _domain in KNOWN_TECH_TOPICS:
            if re.search(rf"\b{re.escape(token)}\b", lowered):
                if canonical_title.lower() in seen_titles:
                    continue
                seen_titles.add(canonical_title.lower())
                is_continuation = bool(
                    re.search(
                        rf"(?:continuer|approfondir|améliorer|progresser\s+en)\s+[^,\.]*{re.escape(token)}",
                        lowered,
                    )
                )
                existing_sk = existing_skills.get(canonical_title.lower())
                inferred_current = (
                    existing_sk.current_level
                    if existing_sk is not None and existing_sk.current_level > 0
                    else None
                )
                extracted.append(
                    ExtractedObjectiveCandidate(
                        kind="personal_goal",
                        category=cat.value,
                        title=canonical_title,
                        goal=(
                            f"Approfondir {canonical_title} et valider le niveau supérieur par des exercices pratiques."
                            if is_continuation
                            else f"Maîtriser les fondamentaux de {canonical_title} et réaliser un mini-projet vérifiable."
                        ),
                        current_level=inferred_current,
                        target_level=existing_sk.target_level if existing_sk else None,
                        priority=TaskPriority.high if len(extracted) == 0 else TaskPriority.normal,
                        is_primary=len(extracted) == 0,
                        deliverables=[f"Exercices corrigés et livrable pratique {canonical_title}"],
                        validation_conditions=[
                            f"Réussir une évaluation pratique vérifiée sur {canonical_title} avec preuve admissible"
                        ],
                        next_action=f"Réaliser la première séance ciblée sur {canonical_title}",
                    )
                )

        # 2. Détection explicite de projets (« construire des projets pratiques », « créer une application ... »)
        proj_match = re.search(
            r"(?:construire|créer|développer|lancer|réaliser)\s+(?:des\s+|un\s+|une\s+)?(projets?\s+[^\.,;!\n]{2,60}|application\s+[^\.,;!\n]{2,60}|plateforme\s+[^\.,;!\n]{2,60}|portfolio[^\.,;!\n]{0,40})",
            combined,
            re.IGNORECASE,
        )
        if proj_match:
            raw_proj = proj_match.group(1).strip().rstrip(".")
            proj_title = raw_proj[0].upper() + raw_proj[1:]
            if proj_title.lower() not in seen_titles:
                seen_titles.add(proj_title.lower())
                extracted.append(
                    ExtractedObjectiveCandidate(
                        kind="project",
                        category=ObjectiveCategory.project.value,
                        title=proj_title[:140],
                        goal=f"Concevoir, tester et livrer « {proj_title} » avec un dépôt ou livrable vérifiable.",
                        priority=TaskPriority.normal,
                        is_primary=False,
                        deliverables=["Prototype fonctionnel", "Code source testé et documenté"],
                        validation_conditions=[
                            "Tous les livrables du projet sont terminés et vérifiés"
                        ],
                        next_action=f"Définir l’architecture et le premier livrable de « {proj_title} »",
                    )
                )

        if not extracted:
            fallback_title = payload.message.strip()[:80]
            extracted.append(
                ExtractedObjectiveCandidate(
                    kind="personal_goal",
                    category=ObjectiveCategory.learning_goal.value,
                    title=fallback_title,
                    goal=f"Progresser sur « {fallback_title} » avec des résultats mesurables.",
                    priority=TaskPriority.high,
                    is_primary=True,
                    deliverables=[f"Livrable pratique sur {fallback_title}"],
                    validation_conditions=["Évaluation pratique validée avec preuve"],
                    next_action=f"Démarrer la première étape sur {fallback_title}",
                )
            )

        # 3. Extraction stricte UNIQUEMENT des informations explicitement fournies (ne JAMAIS inventer)
        stated_current_level: int | str | None = known.get("current_level")
        if stated_current_level is None:
            if re.search(r"\b(débutant|niveau\s*0|niveau\s*1|aucune\s+base)\b", lowered):
                stated_current_level = "Débutant (niveau 1)"
            elif re.search(r"\b(intermédiaire|niveau\s*2|niveau\s*3|quelques\s+bases)\b", lowered):
                stated_current_level = "Intermédiaire (niveau 2 à 3)"
            elif re.search(r"\b(avancé|niveau\s*4|niveau\s*5)\b", lowered):
                stated_current_level = "Avancé (niveau 4)"

        stated_target_level: int | str | None = known.get("target_level")
        if stated_target_level is None:
            target_m = re.search(r"niveau\s+visé\s*[:\-]?\s*([0-5]|avancé|intermédiaire|autonome)", lowered)
            if target_m:
                stated_target_level = target_m.group(1)

        stated_weekly_minutes: int | None = known.get("available_time_weekly_minutes")
        if stated_weekly_minutes is None:
            hours_m = re.search(r"(\d+)\s*(?:h|heures?)\s*(?:par\s+semaine|/semaine|hebdo)", lowered)
            min_m = re.search(r"(\d{2,4})\s*min(?:utes?)?\s*(?:par\s+semaine|/semaine|hebdo)", lowered)
            if hours_m:
                stated_weekly_minutes = int(hours_m.group(1)) * 60
            elif min_m:
                stated_weekly_minutes = int(min_m.group(1))

        stated_target_date: str | None = known.get("target_date")
        if stated_target_date is None:
            iso_m = re.search(r"\b(202\d-\d{2}-\d{2})\b", combined)
            weeks_m = re.search(r"\b(?:en|dans|sous)\s+(\d+)\s*(semaines?|mois)\b", lowered)
            if iso_m:
                stated_target_date = iso_m.group(1)
            elif weeks_m:
                stated_target_date = f"{weeks_m.group(1)} {weeks_m.group(2)}"

        stated_motivation: str | None = known.get("motivation")
        if stated_motivation is None:
            mot_m = re.search(
                r"(?:pour|afin\s+de|parce\s+que|objectif\s+professionnel\s*:?)\s+([^\.,!\n]{5,140})",
                combined,
                re.IGNORECASE,
            )
            if mot_m:
                stated_motivation = mot_m.group(1).strip()

        stated_priority: str | None = known.get("priority")
        if stated_priority is None and extracted:
            primary_cand = next((c for c in extracted if c.is_primary), extracted[0])
            secondary_titles = [c.title for c in extracted if c.title != primary_cand.title]
            if secondary_titles:
                stated_priority = (
                    f"Priorité principale proposée : {primary_cand.title} "
                    f"(objectifs secondaires : {', '.join(secondary_titles)})"
                )
            else:
                stated_priority = f"Priorité principale : {primary_cand.title}"

        # Propagation sur les candidats si l'utilisateur a précisé le temps hebdomadaire
        if stated_weekly_minutes is not None and extracted:
            per_obj = max(60, stated_weekly_minutes // len(extracted))
            for cand in extracted:
                cand.weekly_target_minutes = per_obj

        # 4. Identification des champs manquants et questions progressives
        missing_fields: list[str] = []
        questions: list[str] = []

        if stated_current_level is None:
            missing_fields.append("current_level")
            questions.append(
                "Quel est ton niveau actuel sur chacun de ces sujets (ex. débutant sur React, bases acquises sur Python) ?"
            )
        if stated_weekly_minutes is None:
            missing_fields.append("available_time_weekly_minutes")
            questions.append(
                "Combien d’heures par semaine souhaites-tu consacrer à tes objectifs personnels hors cours universitaires ?"
            )
        if stated_target_date is None:
            missing_fields.append("target_date")
            questions.append(
                "As-tu une échéance cible particulière (ex. fin de semestre, stage, projet dans 4 semaines) ?"
            )
        if stated_target_level is None:
            missing_fields.append("target_level")
        if stated_motivation is None:
            missing_fields.append("motivation")

        all_deliverables = [d for c in extracted for d in c.deliverables]
        all_conditions = [v for c in extracted for v in c.validation_conditions]

        obj_lines = "\n".join(
            f"  {idx + 1}. **{c.title}** ({'Projet' if c.kind == 'project' else 'Objectif personnel'}) : {c.goal}"
            for idx, c in enumerate(extracted)
        )
        q_lines = "\n".join(f"- {q}" for q in questions)

        summary_md = (
            "### Récapitulatif structuré de vos objectifs et projets\n"
            f"- **Objectifs identifiés ({len(extracted)})** :\n{obj_lines}\n"
            f"- **Niveau actuel** : {stated_current_level or 'Non précisé (à confirmer, aucune valeur inventée)'}\n"
            f"- **Niveau visé** : {stated_target_level or 'Autonomie pratique vérifiée (à préciser)'}\n"
            f"- **Priorité** : {stated_priority or 'À arbitrer'}\n"
            f"- **Motivation** : {stated_motivation or 'Progression personnelle et projets pratiques'}\n"
            f"- **Temps disponible** : {f'{stated_weekly_minutes} min / semaine' if stated_weekly_minutes is not None else 'Non précisé (à confirmer)'}\n"
            f"- **Échéance éventuelle** : {stated_target_date or 'Aucune échéance fixe déclarée'}\n"
            f"- **Livrables attendus** : {', '.join(all_deliverables)}\n"
            f"- **Conditions de validation** : {', '.join(all_conditions)}\n"
        )
        if questions:
            summary_md += f"\n**Questions pour compléter votre configuration** :\n{q_lines}\n"
        summary_md += "\n*Confirmez ce récapitulatif pour enregistrer vos objectifs et projets dans votre espace.*"

        return ConversationalIntakeResponse(
            objectives=extracted,
            current_level=stated_current_level,
            target_level=stated_target_level,
            priority=stated_priority,
            motivation=stated_motivation,
            available_time_weekly_minutes=stated_weekly_minutes,
            target_date=stated_target_date,
            expected_deliverables=all_deliverables,
            validation_conditions=all_conditions,
            missing_fields=missing_fields,
            progressive_questions=questions,
            requires_confirmation=True,
            summary_markdown=summary_md,
        )

    def confirm_conversational_intake(
        self,
        user_id: UUID,
        payload: ConfirmIntakeRequest,
    ) -> ConfirmIntakeResponse:
        """Section 3 : Enregistre définitivement les objectifs et projets uniquement après confirmation utilisateur."""
        created_goals: list[PersonalGoalResponse] = []
        created_projects: list[dict[str, Any]] = []
        total_items = max(1, len(payload.objectives))
        default_per_item = (
            max(60, payload.available_time_weekly_minutes // total_items)
            if payload.available_time_weekly_minutes
            else 120
        )

        chosen_primary = payload.primary_title
        if not chosen_primary and payload.objectives:
            first_primary = next((o for o in payload.objectives if o.is_primary), payload.objectives[0])
            chosen_primary = first_primary.title

        for idx, item in enumerate(payload.objectives):
            is_prim = (
                item.title.lower() == chosen_primary.lower()
                if chosen_primary
                else (idx == 0)
            )
            weekly_min = item.weekly_target_minutes or (
                max(120, default_per_item) if is_prim else max(60, default_per_item // 2)
            )

            if item.kind == "project":
                proj = self._project_service.create_project(
                    user_id,
                    ProjectCreate(
                        name=item.title,
                        category=item.category or "project",
                        description=payload.motivation or item.motivation,
                        goal=item.goal,
                        status=ProjectStatus.active,
                        priority=TaskPriority.high if is_prim else item.priority,
                        motivation=payload.motivation or item.motivation,
                        weekly_target_minutes=weekly_min,
                        next_action=item.next_action or f"Démarrer le premier livrable de {item.title}",
                        deliverables=item.deliverables or ["Premier livrable fonctionnel"],
                        success_criteria=item.validation_conditions
                        or ["Livrables testés et validés"],
                        target_date=payload.target_date,
                    ),
                )
                created_projects.append(proj.model_dump(mode="json"))
            else:
                try:
                    cat_enum = ObjectiveCategory(item.category)
                except ValueError:
                    cat_enum = ObjectiveCategory.learning_goal
                created_goal = self.create_goal(
                    user_id,
                    PersonalGoalCreate(
                        title=item.title,
                        category=cat_enum,
                        description=payload.motivation or item.motivation,
                        goal=item.goal,
                        current_level=item.current_level,
                        target_level=item.target_level or 3,
                        priority=TaskPriority.high if is_prim else item.priority,
                        is_primary=is_prim,
                        motivation=payload.motivation or item.motivation,
                        target_date=payload.target_date,
                        weekly_target_minutes=weekly_min,
                        status=ObjectiveStatus.active,
                        deliverables=item.deliverables,
                        next_action=item.next_action,
                        success_criteria=item.validation_conditions,
                        create_linked_entities=True,
                    ),
                )
                created_goals.append(created_goal)

        return ConfirmIntakeResponse(
            created_goals=created_goals,
            created_projects=created_projects,
            active_priority_title=chosen_primary,
        )

    def generate_unified_plan(
        self,
        user_id: UUID,
        payload: UnifiedPlanGenerateRequest | None = None,
        *,
        now_utc: datetime | None = None,
    ) -> UnifiedPlanResponse:
        """Sections 5, 6, 7, 8 : Moteur de planification unifié combinant cours universitaires, objectifs personnels et projets."""
        req = payload or UnifiedPlanGenerateRequest()
        ref_now = now_utc or datetime.now(timezone.utc)
        profile = self._profile_repo.get(user_id)
        tz_name = profile.timezone if profile else "Africa/Dakar"
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo("UTC")

        local_today = ref_now.astimezone(tz).date()
        if req.target_week_start:
            week_monday = date.fromisoformat(req.target_week_start)
        else:
            week_monday = local_today - timedelta(days=local_today.weekday())
        week_sunday = week_monday + timedelta(days=6)

        all_events = self._schedule_repo.list_by_user(user_id)
        goals = self.list_goals(user_id)
        projects = self._project_repo.list_projects(user_id)
        tasks = self._task_repo.list_by_user(user_id)
        skills = self._skill_repo.list_skills(user_id)
        paths = self._learning_repo.list_paths(user_id)

        active_goals = [g for g in goals if g.status == ObjectiveStatus.active]
        active_projects = [p for p in projects if p.status == ProjectStatus.active]

        # 1. Identifier les obligations universitaires fixes sur la semaine
        academic_fixed_slots: list[UnifiedPlanSlot] = []
        fixed_events_by_date: dict[date, list[ScheduleEventRecord]] = {
            week_monday + timedelta(days=i): [] for i in range(7)
        }
        flexible_existing_events: list[ScheduleEventRecord] = []

        for ev in all_events:
            local_start = ev.starts_at.astimezone(tz)
            local_end = ev.ends_at.astimezone(tz)
            ev_date = local_start.date()
            if not (week_monday <= ev_date <= week_sunday):
                continue
            if _is_academic_fixed_event(ev):
                fixed_events_by_date[ev_date].append(ev)
                dur = max(15, round((ev.ends_at - ev.starts_at).total_seconds() / 60))
                academic_fixed_slots.append(
                    UnifiedPlanSlot(
                        source_category="academic_obligation",
                        is_fixed=True,
                        title=ev.title,
                        day_label=DAY_LABELS_FR[ev_date.weekday()],
                        local_date=ev_date.isoformat(),
                        local_start_time=local_start.strftime("%H:%M"),
                        local_end_time=local_end.strftime("%H:%M"),
                        starts_at=ev.starts_at.isoformat(),
                        ends_at=ev.ends_at.isoformat(),
                        duration_minutes=dur,
                        expected_outcome=f"Assister au cours universitaire « {ev.title} » et prendre des notes exploitables.",
                    )
                )
            else:
                flexible_existing_events.append(ev)

        # Détecter combien d'engagements flexibles existants entraient en conflit avec un cours universitaire fixe
        displaced_conflicts_count = 0
        for flex_ev in flexible_existing_events:
            flex_date = flex_ev.starts_at.astimezone(tz).date()
            for fixed_ev in fixed_events_by_date.get(flex_date, []):
                if do_events_overlap(
                    flex_ev.starts_at, flex_ev.ends_at, fixed_ev.starts_at, fixed_ev.ends_at
                ):
                    displaced_conflicts_count += 1
                    break

        # 2. Gestion des priorités et arbitrages anti-dispersion (Section 6)
        arbitrages: list[str] = []
        adaptations: list[UnifiedPlanAdaptationItem] = []

        primary_title = (
            req.primary_priority_title
            or (profile.active_priority_title if profile else None)
            or next((g.title for g in active_goals if g.is_primary), None)
            or (active_goals[0].title if active_goals else None)
            or (active_projects[0].name if active_projects else None)
        )

        critical_tasks = [
            t
            for t in tasks
            if t.status in (TaskStatus.todo, TaskStatus.in_progress)
            and t.priority == TaskPriority.critical
        ]
        if len(critical_tasks) > 3:
            arbitrages.append(
                f"Règle anti-dispersion : {len(critical_tasks)} tâches critiques détectées (maximum autorisé : 3). "
                "Seules les 3 tâches critiques les plus proches de leur échéance sont retenues cette semaine."
            )

        prioritized_projects = list(active_projects)
        if len(prioritized_projects) > 3:
            overflow_names = ", ".join(p.name for p in prioritized_projects[3:])
            prioritized_projects = prioritized_projects[:3]
            arbitrages.append(
                f"Règle anti-dispersion : {len(active_projects)} projets actifs simultanés (maximum prioritaire : 3). "
                f"Mise en attente recommandée cette semaine pour : {overflow_names}."
            )

        if displaced_conflicts_count > 0:
            arbitrages.append(
                f"{displaced_conflicts_count} séance(s) flexible(s) en conflit avec l’emploi du temps universitaire "
                "ont été déplacées automatiquement vers des créneaux libres."
            )

        # 3. Calcul des fenêtres libres réelles (hors cours universitaires, jours exclus, pause déjeuner 12:30 à 13:30 et marges de 15 min)
        avail_prefs = _parse_availability_preferences(profile.preferences if profile else None)
        study_start_min = int(avail_prefs["study_start_hour"]) * 60
        study_end_min = int(avail_prefs["study_end_hour"]) * 60
        excluded_days = set(avail_prefs["excluded_days"])
        max_daily_pref = int(avail_prefs["max_daily_study_minutes"])

        candidate_windows: list[dict[str, Any]] = []
        recovery_slots: list[UnifiedPlanSlot] = []
        standard_day_windows: tuple[tuple[int, int, int, int], ...] = (
            (8, 30, 10, 0),
            (10, 30, 12, 0),
            (14, 0, 15, 30),
            (16, 0, 17, 30),
            (18, 30, 20, 0),
        )

        for day_offset in range(7):
            cur_date = week_monday + timedelta(days=day_offset)
            day_label = DAY_LABELS_FR[cur_date.weekday()]
            day_fixed = fixed_events_by_date.get(cur_date, [])
            day_fixed_minutes = sum(
                max(0, round((e.ends_at - e.starts_at).total_seconds() / 60)) for e in day_fixed
            )

            # Ajouter un créneau explicite de récupération chaque jour (Section 7)
            if req.include_daily_recovery:
                rec_start = datetime.combine(cur_date, time(12, 30), tzinfo=tz)
                rec_end = datetime.combine(cur_date, time(13, 30), tzinfo=tz)
                recovery_slots.append(
                    UnifiedPlanSlot(
                        source_category="recovery",
                        is_fixed=True,
                        title="Pause déjeuner & récupération cognitive",
                        day_label=day_label,
                        local_date=cur_date.isoformat(),
                        local_start_time="12:30",
                        local_end_time="13:30",
                        starts_at=rec_start.astimezone(timezone.utc).isoformat(),
                        ends_at=rec_end.astimezone(timezone.utc).isoformat(),
                        duration_minutes=60,
                        expected_outcome="Récupération sans écran pour préserver la concentration sur la durée.",
                    )
                )

            if cur_date.weekday() in excluded_days or day_fixed_minutes >= max_daily_pref:
                continue

            # Si la journée compte déjà >= 6h de cours universitaires, limiter à 1 créneau personnel max pour éviter la surcharge
            max_personal_slots_for_day = 1 if day_fixed_minutes >= 360 else 2
            added_for_day = 0

            for h1, m1, h2, m2 in standard_day_windows:
                if added_for_day >= max_personal_slots_for_day:
                    break
                if (h1 * 60 + m1) < study_start_min or (h2 * 60 + m2) > study_end_min:
                    continue
                win_start_local = datetime.combine(cur_date, time(h1, m1), tzinfo=tz)
                win_end_local = datetime.combine(cur_date, time(h2, m2), tzinfo=tz)
                win_start_utc = win_start_local.astimezone(timezone.utc)
                win_end_utc = win_end_local.astimezone(timezone.utc)

                # Vérifier l'absence de conflit avec tout cours universitaire (+ marge de 15 min)
                has_fixed_conflict = any(
                    do_events_overlap(
                        win_start_utc - timedelta(minutes=15),
                        win_end_utc + timedelta(minutes=15),
                        f_ev.starts_at,
                        f_ev.ends_at,
                    )
                    for f_ev in day_fixed
                )
                if has_fixed_conflict:
                    continue

                candidate_windows.append(
                    {
                        "day_label": day_label,
                        "local_date": cur_date.isoformat(),
                        "local_start_time": win_start_local.strftime("%H:%M"),
                        "local_end_time": win_end_local.strftime("%H:%M"),
                        "starts_at": win_start_utc.isoformat(),
                        "ends_at": win_end_utc.isoformat(),
                        "duration_minutes": 90,
                    }
                )
                added_for_day += 1

        # 4. Analyse d'adaptation basée sur les séances passées et retards (Section 8)
        goal_adaptation_notes: dict[UUID, str] = {}
        for g in active_goals:
            last_difficulty: str | None = None
            if g.progress_history:
                for entry in reversed(g.progress_history):
                    if entry.get("difficulties"):
                        last_difficulty = str(entry["difficulties"])
                        break
                    if entry.get("outcome_status") in ("partial", "blocked"):
                        last_difficulty = str(entry.get("result") or "Objectif de séance partiellement atteint")
                        break

            # Vérifier aussi les lacunes d'évaluation sur la compétence liée
            skill_gap: str | None = None
            if g.skill_id is not None:
                assessments = self._skill_repo.list_assessments(user_id, skill_id=g.skill_id)
                for a in sorted(assessments, key=lambda x: x.updated_at, reverse=True):
                    if a.gaps_identified:
                        skill_gap = a.gaps_identified[0]
                        break

            if last_difficulty:
                action = (
                    f"{g.title} : reprendre la notion bloquante ({last_difficulty}) "
                    "et réussir une série d’exercices progressifs avant d’avancer."
                )
                goal_adaptation_notes[g.id] = action
                adaptations.append(
                    UnifiedPlanAdaptationItem(
                        target_title=g.title,
                        target_kind="personal_goal",
                        cause=f"Difficulté enregistrée lors d’une séance précédente : {last_difficulty}",
                        action_taken=action,
                    )
                )
            elif skill_gap:
                action = (
                    f"{g.title} : séance de remédiation ciblée sur « {skill_gap} » "
                    "et nouvel exercice de vérification."
                )
                goal_adaptation_notes[g.id] = action
                adaptations.append(
                    UnifiedPlanAdaptationItem(
                        target_title=g.title,
                        target_kind="personal_goal",
                        cause=f"Lacune identifiée lors d’une évaluation : {skill_gap}",
                        action_taken=action,
                    )
                )
            elif g.is_behind_schedule and g.delay_reason:
                action = (
                    f"{g.title} : créneau prioritaire de rattrapage ciblé sur « {g.next_action or g.goal} » "
                    "avec livrable court et vérifiable."
                )
                goal_adaptation_notes[g.id] = action
                adaptations.append(
                    UnifiedPlanAdaptationItem(
                        target_title=g.title,
                        target_kind="personal_goal",
                        cause=g.delay_reason,
                        action_taken=action,
                    )
                )

        # 5. Construction de la file d'engagements flexibles (Objectif principal -> Projets -> Objectifs secondaires -> Révisions)
        # Ne jamais planifier un objectif simplement parce qu'un créneau libre existe : respecter le budget hebdomadaire
        desired_total = sum(g.weekly_target_minutes for g in active_goals) + sum(
            p.weekly_target_minutes for p in prioritized_projects
        )
        if academic_fixed_slots and desired_total == 0:
            desired_total = 90
        weekly_budget_minutes = (
            req.weekly_available_minutes
            if req.weekly_available_minutes is not None
            else min(max(desired_total, 90), 900)
        )

        primary_goals = [
            g
            for g in active_goals
            if g.is_primary or (primary_title and g.title.lower() == primary_title.lower())
        ]
        if not primary_goals and active_goals:
            primary_goals = [active_goals[0]]
        primary_ids = {g.id for g in primary_goals}
        secondary_goals = [g for g in active_goals if g.id not in primary_ids]

        if secondary_goals:
            sec_names = ", ".join(g.title for g in secondary_goals)
            prim_name = primary_goals[0].title if primary_goals else (primary_title or "Priorité active")
            arbitrages.append(
                f"Arbitrage de priorité : « {prim_name} » reçoit l’allocation principale, "
                f"tandis que les objectifs secondaires ({sec_names}) sont maintenus à fréquence modérée "
                "(1 à 2 séances ciblées/semaine) pour éviter toute dispersion."
            )

        allocation_queue: list[dict[str, Any]] = []

        def _resolve_goal_pedagogy_links(g: PersonalGoalResponse) -> tuple[str | None, str | None, str]:
            mod_id: str | None = None
            les_id: str | None = None
            lesson_title: str | None = None
            if g.learning_path_id is not None:
                mods = self._learning_repo.list_modules(user_id, path_id=g.learning_path_id)
                mods.sort(key=lambda m: m.position)
                if mods:
                    active_mod = next(
                        (m for m in mods if m.status != LearningStatus.completed),
                        mods[0],
                    )
                    mod_id = str(active_mod.id)
                    lessons = self._learning_repo.list_lessons(user_id, module_id=active_mod.id)
                    lessons.sort(key=lambda l: l.position)
                    if lessons:
                        active_les = next(
                            (l for l in lessons if l.status != LearningStatus.completed),
                            lessons[0],
                        )
                        les_id = str(active_les.id)
                        lesson_title = active_les.title

            if g.id in goal_adaptation_notes:
                outcome = goal_adaptation_notes[g.id]
            elif "react" in g.title.lower():
                outcome = "React : étudier les composants et props, réaliser un exercice et fournir le code."
            elif "python" in g.title.lower():
                outcome = "Python : reprendre une notion mal maîtrisée et réussir une série d’exercices."
            elif lesson_title:
                outcome = f"{g.title} : travailler « {lesson_title} », réaliser un exercice pratique et consigner une preuve."
            else:
                deliv = g.deliverables[0] if g.deliverables else "un exercice vérifiable"
                outcome = f"{g.title} : avancer sur « {g.next_action or g.goal} » et produire {deliv}."
            return mod_id, les_id, outcome

        # Objectif principal : jusqu'à 2 séances
        for g in primary_goals:
            mod_id, les_id, outcome = _resolve_goal_pedagogy_links(g)
            slots_needed = 2 if g.weekly_target_minutes >= 120 else 1
            for s_idx in range(slots_needed):
                allocation_queue.append(
                    {
                        "source_category": "personal_goal" if s_idx == 0 else "evaluation",
                        "title": (
                            f"Objectif prioritaire : {g.title}"
                            if s_idx == 0
                            else f"Pratique & évaluation : {g.title}"
                        ),
                        "expected_outcome": outcome,
                        "linked_goal_id": str(g.id),
                        "linked_skill_id": str(g.skill_id) if g.skill_id else None,
                        "linked_path_id": str(g.learning_path_id) if g.learning_path_id else None,
                        "linked_module_id": mod_id,
                        "linked_lesson_id": les_id,
                    }
                )

        # Projets actifs : 1 à 2 séances reliées à leur tâche/livrable
        for p in prioritized_projects:
            proj_tasks = [
                t
                for t in tasks
                if t.project_id == p.id and t.status in (TaskStatus.todo, TaskStatus.in_progress)
            ]
            linked_task = proj_tasks[0] if proj_tasks else None
            deliv_label = (
                (p.deliverables[0] if p.deliverables else None)
                or (linked_task.title if linked_task else None)
                or p.next_action
                or p.goal
            )
            allocation_queue.append(
                {
                    "source_category": "project",
                    "title": f"Projet : {p.name}",
                    "expected_outcome": f"Projet ({p.name}) : terminer le livrable identifié « {deliv_label} ».",
                    "linked_project_id": str(p.id),
                    "linked_task_id": str(linked_task.id) if linked_task else None,
                }
            )

        # Objectifs secondaires : maintenus à faible fréquence (1 séance/semaine, Section 6)
        for g in secondary_goals:
            mod_id, les_id, outcome = _resolve_goal_pedagogy_links(g)
            allocation_queue.append(
                {
                    "source_category": "personal_goal",
                    "title": f"Progression : {g.title}",
                    "expected_outcome": outcome,
                    "linked_goal_id": str(g.id),
                    "linked_skill_id": str(g.skill_id) if g.skill_id else None,
                    "linked_path_id": str(g.learning_path_id) if g.learning_path_id else None,
                    "linked_module_id": mod_id,
                    "linked_lesson_id": les_id,
                }
            )

        # Révision académique si des cours universitaires sont présents
        if academic_fixed_slots:
            first_course = academic_fixed_slots[0].title
            allocation_queue.append(
                {
                    "source_category": "revision",
                    "title": f"Révision universitaire : {first_course}",
                    "expected_outcome": f"Synthétiser le cours « {first_course} » et résoudre une fiche d’exercices de TD/TP.",
                }
            )

        # 6. Attribution des créneaux libres sans jamais dépasser le budget hebdomadaire
        flexible_study_slots: list[UnifiedPlanSlot] = []
        allocated_minutes = 0
        used_win_indices: set[int] = set()

        for item in allocation_queue:
            if allocated_minutes + 60 > weekly_budget_minutes:
                break
            chosen_idx = next(
                (i for i in range(len(candidate_windows)) if i not in used_win_indices),
                None,
            )
            if chosen_idx is None:
                break
            used_win_indices.add(chosen_idx)
            win = candidate_windows[chosen_idx]
            dur = min(int(win["duration_minutes"]), max(60, weekly_budget_minutes - allocated_minutes))

            flexible_study_slots.append(
                UnifiedPlanSlot(
                    source_category=item["source_category"],
                    is_fixed=False,
                    title=item["title"][:140],
                    day_label=win["day_label"],
                    local_date=win["local_date"],
                    local_start_time=win["local_start_time"],
                    local_end_time=win["local_end_time"],
                    starts_at=win["starts_at"],
                    ends_at=win["ends_at"],
                    duration_minutes=dur,
                    expected_outcome=item["expected_outcome"],
                    linked_goal_id=item.get("linked_goal_id"),
                    linked_project_id=item.get("linked_project_id"),
                    linked_skill_id=item.get("linked_skill_id"),
                    linked_path_id=item.get("linked_path_id"),
                    linked_module_id=item.get("linked_module_id"),
                    linked_lesson_id=item.get("linked_lesson_id"),
                    linked_task_id=item.get("linked_task_id"),
                )
            )
            allocated_minutes += dur

        # 7. Répartition quotidienne mêlant obligations universitaires, objectifs, projets et récupération
        daily_breakdown: dict[str, list[UnifiedPlanSlot]] = {
            (week_monday + timedelta(days=i)).isoformat(): [] for i in range(7)
        }
        for slot in [*academic_fixed_slots, *flexible_study_slots, *recovery_slots]:
            if slot.local_date in daily_breakdown:
                daily_breakdown[slot.local_date].append(slot)
        for day_key in daily_breakdown:
            daily_breakdown[day_key].sort(key=lambda s: s.local_start_time)

        total_acad = sum(s.duration_minutes for s in academic_fixed_slots)
        total_goal = sum(
            s.duration_minutes
            for s in flexible_study_slots
            if s.source_category in ("personal_goal", "evaluation", "revision")
        )
        total_proj = sum(
            s.duration_minutes for s in flexible_study_slots if s.source_category == "project"
        )

        return UnifiedPlanResponse(
            week_start=week_monday.isoformat(),
            primary_priority_title=primary_title,
            secondary_objectives=[g.title for g in secondary_goals],
            academic_fixed_slots=academic_fixed_slots,
            flexible_study_slots=flexible_study_slots,
            recovery_slots=recovery_slots,
            daily_breakdown=daily_breakdown,
            arbitrages=arbitrages,
            adaptations=adaptations,
            displaced_conflicts_count=displaced_conflicts_count,
            total_academic_minutes=total_acad,
            total_personal_goal_minutes=total_goal,
            total_project_minutes=total_proj,
            requires_validation=True,
        )

    def apply_unified_plan(
        self,
        user_id: UUID,
        payload: UnifiedPlanApplyRequest,
    ) -> UnifiedPlanApplyResponse:
        """Section 7 : Applique le programme validé, déplace les séances flexibles en conflit et relie chaque séance aux tâches/contenus."""
        now = datetime.now(timezone.utc)
        profile = self._profile_repo.get(user_id)
        tz_name = profile.timezone if profile else "Africa/Dakar"
        try:
            tz = ZoneInfo(tz_name)
        except Exception:
            tz = ZoneInfo("UTC")

        all_events = self._schedule_repo.list_by_user(user_id)
        fixed_events = [ev for ev in all_events if _is_academic_fixed_event(ev)]

        displaced_count = 0
        if payload.replace_existing_flexible_week:
            target_dates = {slot.local_date for slot in payload.flexible_study_slots}
            if payload.week_start:
                w_mon = date.fromisoformat(payload.week_start)
                target_dates |= {(w_mon + timedelta(days=i)).isoformat() for i in range(7)}

            for ev in all_events:
                if _is_academic_fixed_event(ev):
                    continue
                ev_local_date = ev.starts_at.astimezone(tz).date().isoformat()
                overlaps_fixed = any(
                    do_events_overlap(ev.starts_at, ev.ends_at, f.starts_at, f.ends_at)
                    for f in fixed_events
                )
                if overlaps_fixed or ev_local_date in target_dates:
                    if overlaps_fixed:
                        displaced_count += 1
                    self._schedule_repo.delete(user_id, ev.id)

        existing_tasks = self._task_repo.list_by_user(user_id)
        created_events_count = 0
        linked_tasks_created_count = 0

        for slot in payload.flexible_study_slots:
            if slot.is_fixed or slot.source_category in ("academic_obligation", "recovery"):
                continue

            start_dt = datetime.fromisoformat(slot.starts_at)
            end_dt = datetime.fromisoformat(slot.ends_at)

            # Vérifier qu'aucun créneau flexible validé n'empiète sur un cours universitaire fixe
            for f_ev in fixed_events:
                if do_events_overlap(start_dt, end_dt, f_ev.starts_at, f_ev.ends_at):
                    raise AppError(
                        409,
                        "UNIVERSITY_COURSE_CONFLICT",
                        f"Conflit avec le cours universitaire fixe « {f_ev.title} ».",
                    )

            ev_type = (
                ScheduleEventType.project
                if slot.source_category == "project"
                else ScheduleEventType.learning
            )

            # Relier ou créer une tâche concrète avec le résultat attendu (Section 7 : ne pas se limiter à des événements calendrier)
            linked_task_id = UUID(slot.linked_task_id) if slot.linked_task_id else None
            linked_proj_id = UUID(slot.linked_project_id) if slot.linked_project_id else None
            linked_mod_id = UUID(slot.linked_module_id) if slot.linked_module_id else None

            if linked_task_id is None:
                matched_task = next(
                    (
                        t
                        for t in existing_tasks
                        if t.title.lower() == slot.title.lower()
                        and t.status in (TaskStatus.todo, TaskStatus.in_progress)
                    ),
                    None,
                )
                if matched_task is None:
                    new_task = self._task_repo.save(
                        TaskRecord(
                            id=uuid4(),
                            user_id=user_id,
                            title=slot.title[:140],
                            description=f"Résultat attendu : {slot.expected_outcome}",
                            status=TaskStatus.todo,
                            priority=(
                                TaskPriority.high
                                if slot.source_category in ("personal_goal", "project")
                                else TaskPriority.normal
                            ),
                            due_at=end_dt,
                            completed_at=None,
                            source=TaskSource.ai_proposal,
                            proposal_id=None,
                            project_id=linked_proj_id,
                            module_id=linked_mod_id,
                            created_at=now,
                            updated_at=now,
                        )
                    )
                    existing_tasks.append(new_task)
                    linked_tasks_created_count += 1

            self._schedule_repo.save(
                ScheduleEventRecord(
                    id=uuid4(),
                    user_id=user_id,
                    title=slot.title[:140],
                    type=ev_type,
                    starts_at=start_dt,
                    ends_at=end_dt,
                    notes=f"Résultat attendu : {slot.expected_outcome}",
                    source=ScheduleEventSource.ai_proposal,
                    created_at=now,
                    updated_at=now,
                )
            )
            created_events_count += 1

        if payload.primary_priority_title and profile is not None:
            self._profile_repo.save(
                profile.model_copy(
                    update={
                        "active_priority_title": payload.primary_priority_title.strip()[:200],
                        "updated_at": now,
                    }
                )
            )

        updated_profile = self._profile_repo.get(user_id)
        return UnifiedPlanApplyResponse(
            created_events_count=created_events_count,
            displaced_conflicts_count=displaced_count,
            linked_tasks_created_count=linked_tasks_created_count,
            active_priority_title=updated_profile.active_priority_title if updated_profile else None,
        )
