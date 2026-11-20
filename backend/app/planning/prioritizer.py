from __future__ import annotations

from datetime import datetime
from app.planning.collector import PlanningContextSnapshot, _ensure_utc
from app.schemas.planning import LearningPriorityItem


class LearningPrioritizer:
    """Classe les apprentissages, révisions, tâches et projets par priorité multi-critères."""

    def prioritize(
        self,
        snapshot: PlanningContextSnapshot,
        *,
        focus_subject: str | None = None,
        exam_title: str | None = None,
        exam_at: datetime | None = None,
    ) -> list[LearningPriorityItem]:
        now = snapshot.collected_at
        items: list[LearningPriorityItem] = []
        focus_l = (focus_subject or "").strip().lower()
        long_term_text = " ".join(snapshot.ai_memory.long_term_goals).lower() if snapshot.ai_memory else ""

        # 0. Examen explicite fourni dans la requête courante
        if exam_title and exam_at:
            ex_utc = _ensure_utc(exam_at) or now
            hours_left = max(0.0, (ex_utc - now).total_seconds() / 3600.0)
            urgency = self._urgency_from_hours(hours_left, is_exam=True)
            items.append(
                LearningPriorityItem(
                    source_type="exam_revision",
                    source_id=None,
                    title=f"Révision {exam_title}",
                    subject=exam_title,
                    domain="Académique",
                    score=round(urgency + 25.0 + 18.0 + 10.0, 2),
                    urgency_score=urgency,
                    blocking_score=25.0,
                    strategic_score=18.0,
                    effort_score=10.0,
                    deficit_score=10.0,
                    deadline_at=ex_utc,
                    recommended_minutes=180 if hours_left <= 168 else 90,
                    reasons=[
                        f"Examen « {exam_title} » prévu dans {max(1, int(hours_left // 24))} jours."
                    ],
                )
            )
        elif exam_title and not exam_at:
            matched_exam = next(
                (ev for ev in snapshot.upcoming_exams if exam_title.lower() in ev.title.lower()),
                None,
            )
            if matched_exam is None:
                items.append(
                    LearningPriorityItem(
                        source_type="exam_revision",
                        source_id=None,
                        title=f"Révision {exam_title}",
                        subject=exam_title,
                        domain="Académique",
                        score=round(24.0 + 20.0 + 16.0 + 8.0, 2),
                        urgency_score=24.0,
                        blocking_score=20.0,
                        strategic_score=16.0,
                        effort_score=8.0,
                        deficit_score=8.0,
                        deadline_at=None,
                        recommended_minutes=120,
                        reasons=[
                            f"Révision priorisée pour « {exam_title} » (date d'examen non renseignée : aucune date inventée)."
                        ],
                    )
                )

        # 1. Examens détectés dans l'emploi du temps
        for ev in snapshot.upcoming_exams:
            ev_s = _ensure_utc(ev.starts_at) or now
            if exam_title and exam_title.lower() in ev.title.lower():
                continue
            hours_left = max(0.0, (ev_s - now).total_seconds() / 3600.0)
            if hours_left > 24 * 21:
                continue
            urgency = self._urgency_from_hours(hours_left, is_exam=True)
            is_focus = bool(focus_l and focus_l in ev.title.lower())
            strategic = 18.0 + (10.0 if is_focus else 0.0)
            items.append(
                LearningPriorityItem(
                    source_type="exam_revision",
                    source_id=str(ev.id),
                    title=f"Préparation : {ev.title}",
                    subject=ev.title,
                    domain="Académique",
                    score=round(urgency + 18.0 + strategic + 8.0, 2),
                    urgency_score=urgency,
                    blocking_score=18.0,
                    strategic_score=strategic,
                    effort_score=8.0,
                    deficit_score=8.0,
                    deadline_at=ev_s,
                    recommended_minutes=150 if hours_left <= 168 else 90,
                    reasons=[
                        f"Échéance d'examen imminente ({max(1, int(hours_left // 24))} j restants)."
                    ],
                )
            )

        # 2. Tâches ouvertes & tâches en retard
        active_task_id = snapshot.profile.active_priority_task_id if snapshot.profile else None
        active_project_id = snapshot.profile.active_priority_project_id if snapshot.profile else None
        for task in snapshot.open_tasks:
            due = _ensure_utc(task.due_at)
            is_overdue = due is not None and due < now
            hours_left = ((due - now).total_seconds() / 3600.0) if due is not None else 9999.0
            urgency = 36.0 if is_overdue else self._urgency_from_hours(hours_left, is_exam=False)
            blocking = 16.0 if (active_task_id == task.id or task.priority.value == "critical") else 6.0
            if task.status.value == "in_progress":
                blocking += 4.0
            strategic = {"critical": 18.0, "high": 14.0, "normal": 8.0, "low": 4.0}.get(
                task.priority.value, 8.0
            )
            if focus_l and focus_l in f"{task.title} {task.description or ''}".lower():
                strategic += 12.0
            reasons = []
            if is_overdue:
                reasons.append("Tâche en retard à replanifier en priorité.")
            elif due is not None:
                reasons.append("Tâche avec échéance proche.")
            else:
                reasons.append(f"Priorité {task.priority.value}.")
            items.append(
                LearningPriorityItem(
                    source_type="task",
                    source_id=str(task.id),
                    title=task.title,
                    subject=task.title,
                    domain="Organisation",
                    score=round(urgency + blocking + strategic + 6.0, 2),
                    urgency_score=urgency,
                    blocking_score=blocking,
                    strategic_score=strategic,
                    effort_score=6.0,
                    deficit_score=4.0,
                    deadline_at=due,
                    recommended_minutes=90 if (is_overdue or task.priority.value in ("critical", "high")) else 60,
                    reasons=reasons,
                )
            )

        # 3. Remédiation sur évaluations/soumissions échouées (débloque l'avancement)
        skill_map = {s.id: s for s in snapshot.skills}
        remediated_skills: set[str] = set()
        for ass in snapshot.failed_assessments:
            sk = skill_map.get(ass.skill_id)
            subj = sk.name if sk else ass.prompt_title
            remediated_skills.add(subj.lower())
            items.append(
                LearningPriorityItem(
                    source_type="skill_remediation",
                    source_id=str(ass.id),
                    title=f"Remédiation : {subj}",
                    subject=subj,
                    domain=sk.domain if sk else "Compétence",
                    score=round(14.0 + 25.0 + 14.0 + 14.0, 2),
                    urgency_score=14.0,
                    blocking_score=25.0,
                    strategic_score=14.0,
                    effort_score=8.0,
                    deficit_score=14.0,
                    recommended_minutes=90,
                    reasons=[
                        f"Évaluation précédente non validée — lacunes à consolider avant le niveau suivant."
                    ],
                )
            )

        # 4. Cours intelligents actifs
        course_subjects_seen: set[str] = set()
        for course in snapshot.active_courses:
            cid = str(course.id)
            course_subjects_seen.add(course.subject.strip().lower())
            subs = snapshot.course_submissions_by_course.get(cid, [])
            has_failed_sub = any(s.passed is False or (s.score is not None and s.score < 70) for s in subs)
            lessons = snapshot.course_lessons_by_course.get(cid, [])
            pending_lessons = [ls for ls in lessons if ls.status.value != "completed"]
            blocking = 22.0 if has_failed_sub else (12.0 if pending_lessons else 8.0)
            strategic = 14.0
            if focus_l and (focus_l in course.subject.lower() or focus_l in course.title.lower()):
                strategic += 14.0
            if course.subject.lower() in long_term_text:
                strategic += 6.0
            recent_mins = snapshot.work_history.minutes_by_subject_14d.get(course.subject.lower(), 0)
            deficit = 12.0 if recent_mins < 90 else (7.0 if recent_mins < 180 else 3.0)
            reasons = [
                f"Cours actif (niveau {course.current_level}/{course.total_levels})."
            ]
            if has_failed_sub:
                reasons.append("Exercice échoué nécessitant une consolidation.")
            items.append(
                LearningPriorityItem(
                    source_type="course",
                    source_id=cid,
                    title=course.title,
                    subject=course.subject,
                    domain=course.domain,
                    score=round(8.0 + blocking + strategic + deficit + 6.0, 2),
                    urgency_score=8.0,
                    blocking_score=blocking,
                    strategic_score=strategic,
                    effort_score=6.0,
                    deficit_score=deficit,
                    recommended_minutes=120,
                    reasons=reasons,
                )
            )

        # 5. Objectifs personnels actifs (exclut strictement paused via active_goals)
        for goal in snapshot.active_goals:
            goal_subj_l = goal.title.strip().lower()
            due = _ensure_utc(goal.target_date)
            hours_left = ((due - now).total_seconds() / 3600.0) if due else 9999.0
            urgency = self._urgency_from_hours(hours_left, is_exam=False) if due else 6.0
            strategic = 20.0 if goal.is_primary else {"critical": 17.0, "high": 14.0, "normal": 10.0, "low": 5.0}.get(goal.priority.value, 10.0)
            if focus_l and (focus_l in goal_subj_l or focus_l in goal.goal.lower()):
                strategic += 14.0
            level_gap = max(0, (goal.target_level or 2) - (goal.current_level or 0))
            deficit = min(14.0, level_gap * 3.5 + 3.0)
            # Éviter un doublon exact si déjà un cours actif porte exactement le même id lié
            if goal.course_id and str(goal.course_id) in {str(c.id) for c in snapshot.active_courses}:
                continue
            reasons = [
                "Objectif principal prioritaire." if goal.is_primary else f"Objectif personnel ({goal.priority.value})."
            ]
            if goal_subj_l in course_subjects_seen:
                strategic -= 2.0  # Favorise un léger équilibrage si un cours couvre déjà ce sujet
            items.append(
                LearningPriorityItem(
                    source_type="personal_goal",
                    source_id=str(goal.id),
                    title=goal.title,
                    subject=goal.title,
                    domain=goal.category.value,
                    score=round(urgency + 10.0 + strategic + deficit + 6.0, 2),
                    urgency_score=urgency,
                    blocking_score=10.0,
                    strategic_score=strategic,
                    effort_score=6.0,
                    deficit_score=deficit,
                    deadline_at=due,
                    recommended_minutes=max(60, min(goal.weekly_target_minutes or 120, 240)),
                    reasons=reasons,
                )
            )

        # 6. Projets actifs (exclut paused)
        for project in snapshot.active_projects:
            due = _ensure_utc(project.target_date)
            hours_left = ((due - now).total_seconds() / 3600.0) if due else 9999.0
            urgency = self._urgency_from_hours(hours_left, is_exam=False) if due else 5.0
            blocking = 14.0 if active_project_id == project.id else 7.0
            strategic = {"critical": 16.0, "high": 13.0, "normal": 9.0, "low": 4.0}.get(
                project.priority.value, 9.0
            )
            if focus_l and focus_l in project.name.lower():
                strategic += 10.0
            items.append(
                LearningPriorityItem(
                    source_type="project",
                    source_id=str(project.id),
                    title=project.name,
                    subject=project.name,
                    domain="Projet",
                    score=round(urgency + blocking + strategic + 8.0, 2),
                    urgency_score=urgency,
                    blocking_score=blocking,
                    strategic_score=strategic,
                    effort_score=5.0,
                    deficit_score=6.0,
                    deadline_at=due,
                    recommended_minutes=max(60, min(project.weekly_target_minutes or 120, 240)),
                    reasons=["Projet actif nécessitant une progression régulière."],
                )
            )

        # 7. Parcours pédagogiques actifs (exclut ceux liés à un cours ou à un objectif en pause)
        inactive_statuses = {"paused", "completed", "cancelled", "archived"}
        paused_subjects = (
            {g.title.strip().lower() for g in snapshot.personal_goals if g.status.value in inactive_statuses}
            | {c.subject.strip().lower() for c in snapshot.courses if c.status.value in inactive_statuses}
            | {p.name.strip().lower() for p in snapshot.projects if p.status.value in inactive_statuses}
        )
        paused_path_ids = (
            {
                str(g.learning_path_id)
                for g in snapshot.personal_goals
                if g.learning_path_id and g.status.value in inactive_statuses
            }
            | {
                str(c.learning_path_id)
                for c in snapshot.courses
                if c.learning_path_id and c.status.value in inactive_statuses
            }
        )
        paused_skill_ids = (
            {
                str(g.skill_id)
                for g in snapshot.personal_goals
                if g.skill_id and g.status.value in inactive_statuses
            }
            | {
                str(c.skill_id)
                for c in snapshot.courses
                if c.skill_id and c.status.value in inactive_statuses
            }
        )
        linked_lp_ids = {str(c.learning_path_id) for c in snapshot.courses if c.learning_path_id} | {
            str(g.learning_path_id) for g in snapshot.personal_goals if g.learning_path_id
        }
        for lp in snapshot.active_learning_paths:
            lp_title_l = lp.title.strip().lower()
            if (
                str(lp.id) in linked_lp_ids
                or str(lp.id) in paused_path_ids
                or lp_title_l in paused_subjects
                or any(lp_title_l == f"parcours : {ps}" for ps in paused_subjects)
            ):
                continue
            strategic = 11.0 + (10.0 if focus_l and focus_l in lp.title.lower() else 0.0)
            items.append(
                LearningPriorityItem(
                    source_type="learning_path",
                    source_id=str(lp.id),
                    title=lp.title,
                    subject=lp.title,
                    domain="Parcours",
                    score=round(6.0 + 10.0 + strategic + 8.0, 2),
                    urgency_score=6.0,
                    blocking_score=10.0,
                    strategic_score=strategic,
                    effort_score=6.0,
                    deficit_score=8.0,
                    recommended_minutes=120,
                    reasons=["Parcours pédagogique en cours."],
                )
            )

        # 8. Compétences non encore liées à un cours/objectif explicite (exclut les sujets en pause)
        represented = {it.subject.strip().lower() for it in items}
        for sk in snapshot.skills:
            gap = (sk.target_level or 3) - sk.current_level
            if (
                gap <= 0
                or sk.name.strip().lower() in represented
                or sk.name.lower() in remediated_skills
                or str(sk.id) in paused_skill_ids
                or sk.name.strip().lower() in paused_subjects
            ):
                continue
            deficit = min(14.0, gap * 3.5)
            strategic = 10.0 + (10.0 if focus_l and focus_l in sk.name.lower() else 0.0)
            items.append(
                LearningPriorityItem(
                    source_type="skill",
                    source_id=str(sk.id),
                    title=f"Monter en compétence : {sk.name}",
                    subject=sk.name,
                    domain=sk.domain,
                    score=round(4.0 + 8.0 + strategic + deficit + 5.0, 2),
                    urgency_score=4.0,
                    blocking_score=8.0,
                    strategic_score=strategic,
                    effort_score=5.0,
                    deficit_score=deficit,
                    recommended_minutes=90,
                    reasons=[f"Écart de compétence ({sk.current_level} → {sk.target_level or 3})."],
                )
            )

        items.sort(key=lambda x: (-x.score, x.deadline_at or datetime.max.replace(tzinfo=now.tzinfo)))
        return items

    def _urgency_from_hours(self, hours_left: float, *, is_exam: bool) -> float:
        if hours_left <= 0:
            return 38.0
        if hours_left <= 48:
            return 38.0 if is_exam else 32.0
        if hours_left <= 7 * 24:
            return 32.0 if is_exam else 24.0
        if hours_left <= 14 * 24:
            return 22.0 if is_exam else 16.0
        if hours_left <= 30 * 24:
            return 12.0 if is_exam else 9.0
        return 4.0
