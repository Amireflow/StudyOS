from __future__ import annotations

from app.planning.collector import PlanningContextSnapshot
from app.repositories.courses_sql import CourseRecord
from app.schemas.common import CourseLanguage
from app.schemas.courses import CoursePreviewRequest
from app.services.courses_service import CourseService
from app.schemas.planning import LearningPriorityItem, PedagogicalStepPayload
from app.services.course_generator import build_course_blueprint, generate_level_content


class SessionContentResolver:
    """Résout le contenu pédagogique exact de chaque créneau en respectant les prérequis."""

    def __init__(self, *, course_service: CourseService | None = None) -> None:
        self._course_service = course_service
        self._preview_cache: dict[str, dict[str, object]] = {}

    def resolve_for_priority(
        self,
        snapshot: PlanningContextSnapshot,
        priority: LearningPriorityItem,
    ) -> PedagogicalStepPayload:
        subj_l = priority.subject.strip().lower()

        # 1. Cours existant directement ciblé ou correspondant au sujet
        matched_course = self._find_matching_course(snapshot, priority)
        if matched_course is not None:
            return self._resolve_from_course(snapshot, matched_course, priority)

        # 2. Remédiation sur évaluation de compétence échouée
        for ass in snapshot.failed_assessments:
            if (
                priority.source_type == "skill_remediation" and str(ass.id) == priority.source_id
            ) or subj_l in ass.prompt_title.lower():
                gaps = list(ass.gaps_identified[:4])
                return PedagogicalStepPayload(
                    content_source="skill_assessment_remediation",
                    skill_id=ass.skill_id,
                    skill_name=priority.subject,
                    remediation_needed=True,
                    remediation_reason=ass.remediation_recommendation
                    or f"Consolidation requise suite à l'évaluation « {ass.prompt_title} ».",
                    blocked_prerequisites=gaps,
                    exercises_focus=gaps or [f"Revoir les fondamentaux de {priority.subject}"],
                    deliverables=["Exercice corrigé ciblant les lacunes identifiées"],
                    recommended_session_type="remediation",
                    next_step_summary=f"Remédiation ciblée sur {', '.join(gaps[:2]) or priority.subject}.",
                )

        # 3. Parcours pédagogique existant
        matched_path = self._find_matching_path(snapshot, priority)
        if matched_path is not None:
            return self._resolve_from_learning_path(snapshot, matched_path.id, matched_path.title)

        # 4. Tâche ou projet concret
        if priority.source_type == "project":
            proj = next(
                (p for p in snapshot.active_projects if str(p.id) == priority.source_id),
                None,
            )
            if proj is not None:
                step_titles = [
                    str(s.get("title") or "").strip()
                    for s in (proj.steps or [])
                    if isinstance(s, dict) and s.get("status") not in ("done", "completed")
                ]
                action = proj.next_action or (step_titles[0] if step_titles else f"Avancer sur {proj.name}")
                return PedagogicalStepPayload(
                    content_source="project_roadmap",
                    deliverables=list(proj.deliverables or [])[:3],
                    exercises_focus=step_titles[:3] or [action],
                    recommended_session_type="project",
                    next_step_summary=action,
                )

        if priority.source_type == "task":
            task = next(
                (t for t in snapshot.open_tasks if str(t.id) == priority.source_id),
                None,
            )
            if task is not None:
                return PedagogicalStepPayload(
                    content_source="task_backlog",
                    module_id=task.module_id,
                    exercises_focus=[task.description or task.title],
                    deliverables=[f"Terminer : {task.title}"],
                    recommended_session_type="review"
                    if any(k in task.title.lower() for k in ("révis", "exam", "td", "tp", "devoir"))
                    else "deep_work",
                    next_step_summary=task.description or f"Exécuter la tâche « {task.title} ».",
                )

        # 5. Aucun cours existant : synthèse structurée via le générateur interne StudyOS
        return self._resolve_preview_course_step(priority, user_id=snapshot.user_id)

    def _find_matching_course(
        self,
        snapshot: PlanningContextSnapshot,
        priority: LearningPriorityItem,
    ) -> CourseRecord | None:
        if priority.source_type == "course" and priority.source_id:
            for c in snapshot.active_courses:
                if str(c.id) == priority.source_id:
                    return c
        subj_l = priority.subject.strip().lower()
        for c in snapshot.active_courses:
            if c.subject.strip().lower() == subj_l or subj_l in c.subject.lower() or c.subject.lower() in subj_l:
                return c
        if priority.source_type == "personal_goal" and priority.source_id:
            goal = next((g for g in snapshot.active_goals if str(g.id) == priority.source_id), None)
            if goal and goal.course_id:
                for c in snapshot.active_courses:
                    if c.id == goal.course_id:
                        return c
        return None

    def _resolve_from_course(
        self,
        snapshot: PlanningContextSnapshot,
        course: CourseRecord,
        priority: LearningPriorityItem,
    ) -> PedagogicalStepPayload:
        cid = str(course.id)
        levels = snapshot.course_levels_by_course.get(cid, [])
        lessons = snapshot.course_lessons_by_course.get(cid, [])
        submissions = snapshot.course_submissions_by_course.get(cid, [])

        # Respect strict de l'ordre des niveaux : premier niveau non validé accessible
        active_level = next(
            (lv for lv in levels if lv.status.value in ("unlocked", "in_progress")),
            None,
        )
        if active_level is None and levels:
            active_level = next((lv for lv in levels if lv.status.value != "validated"), levels[-1])

        locked_higher = [
            f"Niveau {lv.level_number} : {lv.title}"
            for lv in levels
            if lv.status.value == "locked"
        ]

        level_lessons = [
            ls
            for ls in lessons
            if (active_level is None or ls.level_id == active_level.id)
        ]
        level_lessons.sort(key=lambda ls: ls.position)

        # Détecter si une soumission récente sur ce cours/niveau a échoué sans réussite ultérieure
        failed_sub = None
        passed_lesson_ids = {s.lesson_id for s in submissions if s.passed is True and s.lesson_id}
        for sub in sorted(submissions, key=lambda s: s.created_at, reverse=True):
            if (sub.passed is False or (sub.score is not None and sub.score < 70)) and (
                sub.lesson_id is None or sub.lesson_id not in passed_lesson_ids
            ):
                failed_sub = sub
                break

        if failed_sub is not None:
            target_lesson = next(
                (ls for ls in level_lessons if ls.id == failed_sub.lesson_id),
                level_lessons[0] if level_lessons else None,
            )
            improvements = list(failed_sub.improvements[:3]) or [
                failed_sub.next_step_hint or f"Corriger « {failed_sub.title} »"
            ]
            return PedagogicalStepPayload(
                content_source="course_remediation",
                course_id=course.id,
                course_title=course.title,
                level_id=active_level.id if active_level else failed_sub.level_id,
                level_number=active_level.level_number if active_level else course.current_level,
                level_title=active_level.title if active_level else None,
                lesson_id=target_lesson.id if target_lesson else None,
                lesson_title=target_lesson.title if target_lesson else failed_sub.title,
                skill_id=course.skill_id,
                skill_name=course.subject,
                remediation_needed=True,
                remediation_reason=f"Soumission non validée ({failed_sub.score or 0}/100) sur « {failed_sub.title} » : remédiation prioritaire.",
                blocked_prerequisites=locked_higher[:2],
                exercises_focus=improvements,
                deliverables=[f"Reprendre et valider l'exercice « {failed_sub.title} » (>= 70/100)"],
                recommended_session_type="remediation",
                next_step_summary=f"Remédiation sur {target_lesson.title if target_lesson else failed_sub.title} : {improvements[0]}",
            )

        # Leçon suivante non terminée dans l'ordre du niveau courant
        next_lesson = next(
            (ls for ls in level_lessons if ls.status.value != "completed"),
            None,
        )
        if next_lesson is not None:
            ex_titles = [
                str(ex.get("title") or "").strip()
                for ex in (next_lesson.exercises or [])
                if isinstance(ex, dict) and ex.get("title")
            ]
            return PedagogicalStepPayload(
                content_source="existing_course_lesson",
                course_id=course.id,
                course_title=course.title,
                level_id=active_level.id if active_level else None,
                level_number=active_level.level_number if active_level else course.current_level,
                level_title=active_level.title if active_level else None,
                lesson_id=next_lesson.id,
                lesson_title=next_lesson.title,
                skill_id=course.skill_id,
                skill_name=course.subject,
                blocked_prerequisites=locked_higher[:2],
                exercises_focus=ex_titles[:3] or [f"Exercices guidés — {next_lesson.title}"],
                deliverables=[f"Terminer la leçon « {next_lesson.title} » et ses exercices"],
                recommended_session_type="deep_work",
                next_step_summary=f"Niveau {active_level.level_number if active_level else course.current_level} · Leçon {next_lesson.position} : {next_lesson.title}.",
            )

        # Toutes les leçons du niveau terminées -> Mini-projet de validation du niveau
        if active_level is not None:
            return PedagogicalStepPayload(
                content_source="course_level_project",
                course_id=course.id,
                course_title=course.title,
                level_id=active_level.id,
                level_number=active_level.level_number,
                level_title=active_level.title,
                skill_id=course.skill_id,
                skill_name=course.subject,
                blocked_prerequisites=locked_higher[:2],
                exercises_focus=[active_level.project_title or f"Projet Niveau {active_level.level_number}"],
                deliverables=list(active_level.project_deliverables or [])[:3]
                or ["Soumettre le livrable du niveau pour débloquer la suite"],
                recommended_session_type="project",
                next_step_summary=f"Valider le mini-projet du niveau {active_level.level_number} : {active_level.project_title or active_level.title}.",
            )

        return self._resolve_preview_course_step(priority)

    def _find_matching_path(
        self,
        snapshot: PlanningContextSnapshot,
        priority: LearningPriorityItem,
    ):
        if priority.source_type == "learning_path" and priority.source_id:
            for lp in snapshot.active_learning_paths:
                if str(lp.id) == priority.source_id:
                    return lp
        subj_l = priority.subject.strip().lower()
        for lp in snapshot.active_learning_paths:
            if subj_l in lp.title.lower() or lp.title.lower() in subj_l:
                return lp
        return None

    def _resolve_from_learning_path(
        self,
        snapshot: PlanningContextSnapshot,
        path_id,
        path_title: str,
    ) -> PedagogicalStepPayload:
        modules = snapshot.modules_by_path.get(str(path_id), [])
        next_mod = next((m for m in modules if m.status.value != "completed"), None)
        if next_mod is None and modules:
            next_mod = modules[-1]
        if next_mod is not None:
            lessons = snapshot.lessons_by_module.get(str(next_mod.id), [])
            next_les = next((l for l in lessons if l.status.value != "completed"), None)
            later_mods = [
                f"Module {m.position} : {m.title}"
                for m in modules
                if m.position > next_mod.position
            ]
            return PedagogicalStepPayload(
                content_source="learning_path",
                module_id=next_mod.id,
                module_title=next_mod.title,
                lesson_id=next_les.id if next_les else None,
                lesson_title=next_les.title if next_les else None,
                blocked_prerequisites=later_mods[:2],
                exercises_focus=[next_les.title if next_les else next_mod.title],
                deliverables=[f"Valider « {next_les.title if next_les else next_mod.title} »"],
                recommended_session_type="deep_work",
                next_step_summary=f"Parcours « {path_title} » · Module {next_mod.position} ({next_mod.title})"
                + (f" → {next_les.title}" if next_les else ""),
            )
        return PedagogicalStepPayload(
            content_source="learning_path",
            exercises_focus=[path_title],
            deliverables=[f"Compléter le parcours {path_title}"],
            recommended_session_type="deep_work",
            next_step_summary=f"Continuer le parcours « {path_title} ».",
        )

    def _resolve_preview_course_step(
        self,
        priority: LearningPriorityItem,
        *,
        user_id=None,
    ) -> PedagogicalStepPayload:
        subject = priority.subject.strip() or priority.title.strip()
        cache_key = subject.lower()
        cached = self._preview_cache.get(cache_key)
        if cached is None:
            if self._course_service is not None and user_id is not None:
                # Réutilise le vrai service de cours : il récupère la configuration IA
                # propre à cet utilisateur, son fournisseur, sa clé chiffrée et son contexte.
                preview = self._course_service.preview_course(
                    CoursePreviewRequest(
                        subject=subject,
                        language=CourseLanguage.fr,
                        total_levels=3,
                        goal=priority.title[:300],
                    ),
                    user_id=user_id,
                )
                roadmap = preview.levels_roadmap[0] if preview.levels_roadmap else None
                lessons = [
                    {
                        "title": lesson.title,
                        "summary": lesson.summary,
                        "exercises": [{"title": exercise.title} for exercise in lesson.exercises],
                    }
                    for lesson in preview.first_level_lessons
                ]
                cached = {
                    "blueprint": {"title": preview.title},
                    "level1": {
                        "title": roadmap.title if roadmap else f"Niveau 1 : {subject}",
                        "lessons": lessons,
                        "project_deliverables": list(preview.first_level_project_deliverables),
                    },
                }
            else:
                # Repli déterministe conservé pour les tests isolés et le mode local.
                blueprint = build_course_blueprint(
                    subject=subject,
                    language=CourseLanguage.fr,
                    total_levels=3,
                )
                level1 = generate_level_content(
                    subject=subject,
                    language=CourseLanguage.fr,
                    level_number=1,
                    total_levels=3,
                    focus_hint=priority.reasons[0] if priority.reasons else None,
                )
                cached = {"blueprint": blueprint, "level1": level1}
            self._preview_cache[cache_key] = cached

        blueprint = cached["blueprint"]  # type: ignore[assignment]
        level1 = cached["level1"]  # type: ignore[assignment]
        lessons = level1.get("lessons") or []
        first_lesson = lessons[0] if lessons else {}
        lesson_title = str(first_lesson.get("title") or f"Fondamentaux de {subject}")
        lesson_summary = str(first_lesson.get("summary") or "").strip()
        exercises = [
            str(ex.get("title") or "").strip()
            for ex in (first_lesson.get("exercises") or [])
            if isinstance(ex, dict) and ex.get("title")
        ]
        if priority.source_type == "exam_revision":
            return PedagogicalStepPayload(
                content_source="exam_preparation_blueprint",
                course_title=f"Révision intensive : {subject}",
                level_number=1,
                level_title=str(level1.get("title") or f"Socle d'examen {subject}"),
                lesson_title=f"Annales et points clés : {lesson_title}",
                exercises_focus=exercises[:2] or [f"Fiches synthèses et exercices types {subject}"],
                deliverables=[f"Sujet d'entraînement corrigé sur {subject}"],
                recommended_session_type="review",
                next_step_summary=(
                    f"Révision ciblée {subject} : {lesson_title}. "
                    f"{lesson_summary}".strip()
                ),
            )

        summary = (
            f"Cours recommandé « {blueprint.get('title')} », niveau 1 : {lesson_title}. "
            f"{lesson_summary}".strip()
        )
        return PedagogicalStepPayload(
            content_source="course_generator_preview",
            course_title=str(blueprint.get("title") or f"Cours {subject}"),
            level_number=1,
            level_title=str(level1.get("title") or f"Niveau 1 : bases de {subject}"),
            lesson_title=lesson_title,
            exercises_focus=exercises[:3] or [f"Mise en pratique guidée sur {subject}"],
            deliverables=list(level1.get("project_deliverables") or [])[:2]
            or [f"Premier exercice validé sur {lesson_title}"],
            recommended_session_type="deep_work",
            next_step_summary=summary,
        )
