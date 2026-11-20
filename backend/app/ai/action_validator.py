from typing import Any
from uuid import UUID
from pydantic import ValidationError
from app.ai.tool_registry import ToolRegistry
from app.core.errors import AppError
from app.repositories.learning_sql import (
    SqlLearningRepository,
    SqlPersonalGoalRepository,
    SqlProjectRepository,
    SqlSkillRepository,
)
from app.repositories.memory import ScheduleRepository, TaskRepository
from app.repositories.planning_sql import SqlPlanningRepository
from app.schemas.ai import (
    AddEvidenceProposalPayload,
    ArchiveScheduleEventProposalPayload,
    BatchActionsProposalPayload,
    CreateCourseProposalPayload,
    CreateLearningPathProposalPayload,
    CreatePersonalGoalProposalPayload,
    CreateProjectProposalPayload,
    CreateScheduleProposalPayload,
    CreateSkillProposalPayload,
    CreateStudySessionProposalPayload,
    CreateTaskProposalPayload,
    GenerateLearningPlanProposalPayload,
    ManageAvailabilityRuleProposalPayload,
    ParkTaskProposalPayload,
    PauseProjectProposalPayload,
    PlanStrategicActivityProposalPayload,
    ProposeSkillAssessmentPayload,
    RawProposalCandidate,
    RecommendSkillProgressionPayload,
    UpdateLearningPathProposalPayload,
    UpdatePersonalGoalProposalPayload,
    UpdatePreferencesProposalPayload,
    UpdateProjectProposalPayload,
    UpdateScheduleEventProposalPayload,
    UpdateTaskProposalPayload,
)
from app.schemas.common import (
    AiActionType,
    ProjectStatus,
    ScheduleEventSource,
    ScheduleEventType,
    SkillAssessmentStatus,
)
from app.services.assessment_evaluator import (
    pass_threshold_for_level,
    validate_evidence_quality,
)
from app.services.schedule_service import do_events_overlap


class ValidatedProposal:
    def __init__(
        self,
        *,
        action_type: AiActionType,
        title: str,
        explanation: str,
        payload: dict[str, Any],
    ) -> None:
        self.action_type = action_type
        self.title = title
        self.explanation = explanation
        self.payload = payload


class ActionValidator:
    """Valide chaque proposition IA contre la liste blanche ToolRegistry et les schémas métier (AI-01, AI-03)."""

    def __init__(
        self,
        *,
        tool_registry: ToolRegistry,
        task_repo: TaskRepository,
        schedule_repo: ScheduleRepository,
        learning_repo: SqlLearningRepository,
        skill_repo: SqlSkillRepository,
        project_repo: SqlProjectRepository,
        goal_repo: SqlPersonalGoalRepository | None = None,
        planning_repo: SqlPlanningRepository | None = None,
    ) -> None:
        self._tool_registry = tool_registry
        self._task_repo = task_repo
        self._schedule_repo = schedule_repo
        self._learning_repo = learning_repo
        self._skill_repo = skill_repo
        self._project_repo = project_repo
        self._goal_repo = goal_repo
        self._planning_repo = planning_repo

    def validate_candidate(
        self,
        user_id: UUID,
        candidate: RawProposalCandidate,
    ) -> ValidatedProposal:
        if not self._tool_registry.is_allowed_proposal_action(candidate.action_type):
            raise AppError(
                422,
                "UNSUPPORTED_AI_ACTION",
                f"L’action « {candidate.action_type} » n’appartient pas à la liste blanche ToolRegistry.",
            )

        title = candidate.title.strip()
        explanation = candidate.explanation.strip()
        if len(title) < 2 or len(title) > 180:
            raise AppError(422, "VALIDATION_ERROR", "Le titre de la proposition est invalide.")
        if len(explanation) < 2 or len(explanation) > 1000:
            raise AppError(422, "VALIDATION_ERROR", "L’explication de la proposition est invalide.")

        action_enum = AiActionType(candidate.action_type)
        validated_payload = self.validate_action_payload(user_id, action_enum, candidate.payload)

        return ValidatedProposal(
            action_type=action_enum,
            title=title,
            explanation=explanation,
            payload=validated_payload,
        )

    def validate_action_payload(
        self,
        user_id: UUID,
        action_type: AiActionType,
        raw_payload: dict[str, Any],
        *,
        _skip_fks: set[str] | None = None,
    ) -> dict[str, Any]:
        skip_fks = _skip_fks or set()
        try:
            if action_type == AiActionType.create_task:
                model = CreateTaskProposalPayload.model_validate(raw_payload)
                if (
                    "project_id" not in skip_fks
                    and model.project_id is not None
                    and self._project_repo.get(user_id, model.project_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Projet associé introuvable.")
                if (
                    "module_id" not in skip_fks
                    and model.module_id is not None
                    and self._learning_repo.get_module(user_id, model.module_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Module associé introuvable.")
                return {
                    "title": model.title,
                    "description": model.description,
                    "priority": model.priority.value,
                    "due_at": model.due_at.isoformat() if model.due_at else None,
                    "project_id": str(model.project_id) if model.project_id else None,
                    "module_id": str(model.module_id) if model.module_id else None,
                }

            if action_type == AiActionType.update_task:
                model = UpdateTaskProposalPayload.model_validate(raw_payload)
                if "task_id" not in skip_fks and self._task_repo.get(user_id, model.task_id) is None:
                    raise AppError(404, "NOT_FOUND", "Tâche cible introuvable.")
                if (
                    "project_id" not in skip_fks
                    and model.project_id is not None
                    and self._project_repo.get(user_id, model.project_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Projet associé introuvable.")
                if (
                    "module_id" not in skip_fks
                    and model.module_id is not None
                    and self._learning_repo.get_module(user_id, model.module_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Module associé introuvable.")
                return model.model_dump(mode="json", exclude_none=True)

            if action_type == AiActionType.park_task:
                model = ParkTaskProposalPayload.model_validate(raw_payload)
                task = self._task_repo.get(user_id, model.task_id)
                if task is None:
                    raise AppError(404, "NOT_FOUND", "Tâche cible introuvable.")
                return {
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "reason": model.reason,
                }

            if action_type == AiActionType.create_project:
                model = CreateProjectProposalPayload.model_validate(raw_payload)
                if (
                    "goal_id" not in skip_fks
                    and model.goal_id is not None
                    and self._goal_repo is not None
                    and self._goal_repo.get(user_id, model.goal_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Objectif associé introuvable.")
                next_action = model.next_action.strip()
                if model.status == ProjectStatus.active and len(next_action) < 2:
                    next_action = "Définir la première étape concrète"
                out = model.model_copy(update={"next_action": next_action}).model_dump(mode="json")
                return out

            if action_type == AiActionType.update_project:
                model = UpdateProjectProposalPayload.model_validate(raw_payload)
                if "project_id" not in skip_fks and self._project_repo.get(user_id, model.project_id) is None:
                    raise AppError(404, "NOT_FOUND", "Projet cible introuvable.")
                return model.model_dump(mode="json", exclude_none=True)

            if action_type == AiActionType.pause_project:
                model = PauseProjectProposalPayload.model_validate(raw_payload)
                project = self._project_repo.get(user_id, model.project_id)
                if project is None:
                    raise AppError(404, "NOT_FOUND", "Projet cible introuvable.")
                if project.status in (ProjectStatus.completed, ProjectStatus.archived):
                    raise AppError(
                        409,
                        "PROJECT_NOT_PAUSABLE",
                        "Impossible de mettre en pause un projet déjà terminé ou archivé.",
                    )
                return {
                    "project_id": str(project.id),
                    "project_name": project.name,
                    "previous_status": project.status.value,
                    "reason": model.reason,
                }

            if action_type == AiActionType.create_schedule_event:
                model = CreateScheduleProposalPayload.model_validate(raw_payload)
                existing_events = self._schedule_repo.list_by_user(user_id)
                overlapping_events = [
                    ev
                    for ev in existing_events
                    if do_events_overlap(model.starts_at, model.ends_at, ev.starts_at, ev.ends_at)
                ]
                uni_conflicts = [
                    ev.title
                    for ev in overlapping_events
                    if ev.type == ScheduleEventType.course
                    or ev.source == ScheduleEventSource.timetable_import
                ]
                if uni_conflicts and model.type != ScheduleEventType.course:
                    raise AppError(
                        409,
                        "UNIVERSITY_COURSE_CONFLICT",
                        f"Impossible de planifier une séance personnelle sur le créneau du cours universitaire « {uni_conflicts[0]} ».",
                    )
                conflicts = [ev.title for ev in overlapping_events]
                return {
                    "title": model.title,
                    "type": model.type.value,
                    "starts_at": model.starts_at.isoformat(),
                    "ends_at": model.ends_at.isoformat(),
                    "notes": model.notes,
                    "has_conflict": len(conflicts) > 0,
                    "conflicting_titles": conflicts,
                }

            if action_type == AiActionType.update_schedule_event:
                model = UpdateScheduleEventProposalPayload.model_validate(raw_payload)
                ev = self._schedule_repo.get(user_id, model.event_id)
                if ev is None:
                    raise AppError(404, "NOT_FOUND", "Créneau cible introuvable.")
                if (
                    ev.type == ScheduleEventType.course
                    or ev.source == ScheduleEventSource.timetable_import
                ):
                    raise AppError(
                        409,
                        "UNIVERSITY_COURSE_CONFLICT",
                        f"Le cours universitaire « {ev.title} » est protégé et ne peut pas être déplacé automatiquement.",
                    )
                new_start = model.starts_at or ev.starts_at
                new_end = model.ends_at or ev.ends_at
                if new_end <= new_start:
                    raise AppError(
                        422,
                        "VALIDATION_ERROR",
                        "L’heure de fin doit être strictement postérieure au début.",
                    )
                for other in self._schedule_repo.list_by_user(user_id):
                    if other.id == ev.id:
                        continue
                    if (
                        other.type == ScheduleEventType.course
                        or other.source == ScheduleEventSource.timetable_import
                    ) and do_events_overlap(new_start, new_end, other.starts_at, other.ends_at):
                        raise AppError(
                            409,
                            "UNIVERSITY_COURSE_CONFLICT",
                            f"Impossible de déplacer ce créneau sur le cours universitaire « {other.title} ».",
                        )
                return model.model_dump(mode="json", exclude_none=True)

            if action_type == AiActionType.archive_schedule_event:
                model = ArchiveScheduleEventProposalPayload.model_validate(raw_payload)
                ev = self._schedule_repo.get(user_id, model.event_id)
                if ev is None:
                    raise AppError(404, "NOT_FOUND", "Créneau cible introuvable.")
                if (
                    ev.type == ScheduleEventType.course
                    or ev.source == ScheduleEventSource.timetable_import
                ):
                    raise AppError(
                        409,
                        "UNIVERSITY_COURSE_CONFLICT",
                        f"Le cours universitaire « {ev.title} » ne peut pas être supprimé via le copilote.",
                    )
                return {"event_id": str(ev.id), "event_title": ev.title, "reason": model.reason}

            if action_type == AiActionType.create_study_session:
                model = CreateStudySessionProposalPayload.model_validate(raw_payload)
                if (
                    "project_id" not in skip_fks
                    and model.project_id is not None
                    and self._project_repo.get(user_id, model.project_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Projet associé introuvable.")
                if (
                    "task_id" not in skip_fks
                    and model.task_id is not None
                    and self._task_repo.get(user_id, model.task_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Tâche associée introuvable.")
                if (
                    "skill_id" not in skip_fks
                    and model.skill_id is not None
                    and self._skill_repo.get_skill(user_id, model.skill_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Compétence associée introuvable.")
                if (
                    "goal_id" not in skip_fks
                    and model.goal_id is not None
                    and self._goal_repo is not None
                    and self._goal_repo.get(user_id, model.goal_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Objectif associé introuvable.")
                return model.model_dump(mode="json", exclude_none=True)

            if action_type == AiActionType.create_skill:
                if raw_payload.get("current_level") not in (None, 0):
                    raise AppError(
                        422,
                        "VALIDATION_ERROR",
                        "Une nouvelle compétence démarre obligatoirement au niveau 0 (verrou pédagogique).",
                    )
                cleaned_raw = {k: v for k, v in raw_payload.items() if k != "current_level"}
                model = CreateSkillProposalPayload.model_validate(cleaned_raw)
                if (
                    "goal_id" not in skip_fks
                    and model.goal_id is not None
                    and self._goal_repo is not None
                    and self._goal_repo.get(user_id, model.goal_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Objectif associé introuvable.")
                if (
                    "learning_path_id" not in skip_fks
                    and model.learning_path_id is not None
                    and self._learning_repo.get_path(user_id, model.learning_path_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Parcours associé introuvable.")
                out = model.model_dump(mode="json")
                out["current_level"] = 0
                return out

            if action_type == AiActionType.add_skill_evidence:
                model = AddEvidenceProposalPayload.model_validate(raw_payload)
                skill = self._skill_repo.get_skill(user_id, model.skill_id)
                if skill is None:
                    raise AppError(404, "NOT_FOUND", "Compétence cible introuvable.")
                quality = validate_evidence_quality(
                    model.type,
                    model.description,
                    model.reference_url,
                    model.result,
                )
                if not quality.admissible:
                    raise AppError(
                        422,
                        "EVIDENCE_QUALITY_INSUFFICIENT",
                        quality.reason or "Preuve proposée non admissible.",
                    )
                return {
                    "skill_id": str(skill.id),
                    "skill_name": skill.name,
                    "type": model.type.value,
                    "description": model.description,
                    "reference_url": model.reference_url,
                    "result": model.result,
                }

            if action_type == AiActionType.propose_skill_assessment:
                model = ProposeSkillAssessmentPayload.model_validate(raw_payload)
                skill = self._skill_repo.get_skill(user_id, model.skill_id)
                if skill is None:
                    raise AppError(404, "NOT_FOUND", "Compétence cible introuvable.")
                target_level = (
                    model.target_level
                    if model.target_level is not None
                    else min(5, max(1, skill.current_level + 1))
                )
                if target_level < max(1, skill.current_level) or target_level > 5:
                    raise AppError(
                        422,
                        "INVALID_TARGET_LEVEL",
                        "Le niveau visé par l’évaluation proposée est invalide.",
                    )
                if (
                    model.path_id is not None
                    and self._learning_repo.get_path(user_id, model.path_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Parcours associé introuvable.")
                if (
                    model.module_id is not None
                    and self._learning_repo.get_module(user_id, model.module_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Module associé introuvable.")
                if (
                    model.lesson_id is not None
                    and self._learning_repo.get_lesson(user_id, model.lesson_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Leçon associée introuvable.")
                return {
                    "skill_id": str(skill.id),
                    "skill_name": skill.name,
                    "current_level": skill.current_level,
                    "target_level": target_level,
                    "assessment_type": model.assessment_type.value,
                    "prompt_title": model.prompt_title,
                    "prompt_instructions": model.prompt_instructions,
                    "path_id": str(model.path_id) if model.path_id else None,
                    "module_id": str(model.module_id) if model.module_id else None,
                    "lesson_id": str(model.lesson_id) if model.lesson_id else None,
                }

            if action_type == AiActionType.recommend_skill_progression:
                model = RecommendSkillProgressionPayload.model_validate(raw_payload)
                skill = self._skill_repo.get_skill(user_id, model.skill_id)
                if skill is None:
                    raise AppError(404, "NOT_FOUND", "Compétence cible introuvable.")
                assessment = self._skill_repo.get_assessment(user_id, model.assessment_id)
                if assessment is None or assessment.skill_id != skill.id:
                    raise AppError(404, "NOT_FOUND", "Évaluation de compétence introuvable.")
                if assessment.status == SkillAssessmentStatus.approved:
                    raise AppError(
                        409,
                        "ASSESSMENT_ALREADY_APPROVED",
                        "Cette évaluation a déjà été validée et ne peut plus être réutilisée.",
                    )
                if assessment.status != SkillAssessmentStatus.evaluated:
                    raise AppError(
                        409,
                        "ASSESSMENT_NOT_EVALUATED",
                        "Seule une évaluation corrigée (statut evaluated) peut faire l’objet d’une progression.",
                    )
                threshold = pass_threshold_for_level(assessment.target_level)
                if (
                    assessment.passed is not True
                    or assessment.score is None
                    or assessment.score < threshold
                    or assessment.proposed_level is None
                ):
                    raise AppError(
                        422,
                        "ASSESSMENT_RESULT_INSUFFICIENT",
                        "Le résultat de l’évaluation est insuffisant pour recommander une progression.",
                    )
                if model.proposed_level != assessment.proposed_level:
                    raise AppError(
                        422,
                        "PROPOSED_LEVEL_MISMATCH",
                        "Le niveau recommandé par le Copilote ne correspond pas au niveau issu de l’évaluation.",
                    )

                candidate_evidence_ids = (
                    [str(eid) for eid in model.evidence_ids]
                    if model.evidence_ids
                    else list(assessment.evidence_ids)
                )
                if not candidate_evidence_ids:
                    raise AppError(
                        422,
                        "ASSESSMENT_EVIDENCE_REQUIRED",
                        "Au moins une preuve admissible appartenant à l’utilisateur est requise.",
                    )
                assessment_ev_set = set(assessment.evidence_ids)
                verified_ids: list[str] = []
                for raw_eid in candidate_evidence_ids:
                    try:
                        ev_uuid = UUID(str(raw_eid))
                    except ValueError as exc:
                        raise AppError(422, "ASSESSMENT_EVIDENCE_REQUIRED", "UUID de preuve invalide.") from exc
                    if str(ev_uuid) not in assessment_ev_set:
                        raise AppError(
                            422,
                            "EVIDENCE_NOT_LINKED_TO_ASSESSMENT",
                            "La preuve citée n’est pas rattachée à l’évaluation.",
                        )
                    ev = self._skill_repo.get_evidence(user_id, ev_uuid)
                    if ev is None:
                        raise AppError(
                            404,
                            "EVIDENCE_NOT_FOUND",
                            "Preuve introuvable ou appartenant à un autre utilisateur.",
                        )
                    if ev.skill_id != skill.id:
                        raise AppError(
                            422,
                            "EVIDENCE_SKILL_MISMATCH",
                            "La preuve citée appartient à une autre compétence.",
                        )
                    quality = validate_evidence_quality(
                        ev.type, ev.description, ev.reference_url, ev.result
                    )
                    if not quality.admissible:
                        raise AppError(
                            422,
                            "EVIDENCE_QUALITY_INSUFFICIENT",
                            quality.reason or "Preuve liée non admissible.",
                        )
                    verified_ids.append(str(ev_uuid))

                return {
                    "skill_id": str(skill.id),
                    "skill_name": skill.name,
                    "assessment_id": str(assessment.id),
                    "previous_level": skill.current_level,
                    "proposed_level": assessment.proposed_level,
                    "score": assessment.score,
                    "evidence_ids": verified_ids,
                    "decision_reason": model.decision_reason,
                }

            if action_type == AiActionType.create_learning_path:
                model = CreateLearningPathProposalPayload.model_validate(raw_payload)
                return model.model_dump(mode="json")

            if action_type == AiActionType.update_learning_path:
                model = UpdateLearningPathProposalPayload.model_validate(raw_payload)
                if "path_id" not in skip_fks and self._learning_repo.get_path(user_id, model.path_id) is None:
                    raise AppError(404, "NOT_FOUND", "Parcours cible introuvable.")
                return model.model_dump(mode="json", exclude_none=True)

            if action_type == AiActionType.create_personal_goal:
                model = CreatePersonalGoalProposalPayload.model_validate(raw_payload)
                return model.model_dump(mode="json")

            if action_type == AiActionType.update_personal_goal:
                model = UpdatePersonalGoalProposalPayload.model_validate(raw_payload)
                if (
                    "goal_id" not in skip_fks
                    and self._goal_repo is not None
                    and self._goal_repo.get(user_id, model.goal_id) is None
                ):
                    raise AppError(404, "NOT_FOUND", "Objectif cible introuvable.")
                return model.model_dump(mode="json", exclude_none=True)

            if action_type == AiActionType.plan_strategic_activity:
                model = PlanStrategicActivityProposalPayload.model_validate(raw_payload)
                if model.park_only:
                    parked_model = model.model_copy(update={"proposed_slots": []})
                    return parked_model.model_dump(mode="json")

                for idx_a in range(len(model.proposed_slots)):
                    slot_a = model.proposed_slots[idx_a]
                    for idx_b in range(idx_a + 1, len(model.proposed_slots)):
                        slot_b = model.proposed_slots[idx_b]
                        if do_events_overlap(
                            slot_a.starts_at, slot_a.ends_at, slot_b.starts_at, slot_b.ends_at
                        ):
                            raise AppError(
                                422,
                                "INTERNAL_SLOT_OVERLAP",
                                "Deux créneaux proposés dans le même plan se chevauchent.",
                            )

                existing_events = self._schedule_repo.list_by_user(user_id)
                for slot in model.proposed_slots:
                    for ev in existing_events:
                        if do_events_overlap(
                            slot.starts_at, slot.ends_at, ev.starts_at, ev.ends_at
                        ):
                            if (
                                ev.type == ScheduleEventType.course
                                or ev.source == ScheduleEventSource.timetable_import
                            ):
                                raise AppError(
                                    409,
                                    "UNIVERSITY_COURSE_CONFLICT",
                                    f"Conflit avec le cours universitaire « {ev.title} » sur le créneau {slot.day_label} {slot.local_start_time}–{slot.local_end_time}.",
                                )
                            raise AppError(
                                409,
                                "SCHEDULE_CONFLICT_DETECTED",
                                f"Le créneau {slot.day_label} {slot.local_start_time}–{slot.local_end_time} entre en conflit avec l’événement existant « {ev.title} ». Veuillez modifier ou recalculer la proposition.",
                            )

                return model.model_dump(mode="json")

            if action_type == AiActionType.create_course:
                if raw_payload.get("current_level") not in (None, 1):
                    raise AppError(
                        422,
                        "VALIDATION_ERROR",
                        "Un cours démarre obligatoirement au niveau 1 (verrou pédagogique).",
                    )
                model = CreateCourseProposalPayload.model_validate(
                    {k: v for k, v in raw_payload.items() if k != "current_level"}
                )
                return model.model_dump(mode="json")

            if action_type == AiActionType.update_preferences:
                model = UpdatePreferencesProposalPayload.model_validate(raw_payload)
                dumped = model.model_dump(mode="json", exclude_none=True)
                if not dumped:
                    raise AppError(
                        422,
                        "VALIDATION_ERROR",
                        "Au moins une préférence ou disponibilité doit être précisée.",
                    )
                return dumped

            if action_type == AiActionType.manage_availability_rule:
                model = ManageAvailabilityRuleProposalPayload.model_validate(raw_payload)
                if model.recurrence == "weekly" and model.day_of_week is None:
                    raise AppError(
                        422,
                        "VALIDATION_ERROR",
                        "Une règle hebdomadaire exige un jour de semaine (0=lundi .. 6=dimanche).",
                    )
                if model.recurrence in ("weekly", "daily") and (not model.start_time or not model.end_time):
                    raise AppError(
                        422,
                        "VALIDATION_ERROR",
                        "Une règle récurrente exige start_time et end_time (HH:MM).",
                    )
                return model.model_dump(mode="json")

            if action_type == AiActionType.generate_learning_plan:
                model = GenerateLearningPlanProposalPayload.model_validate(raw_payload)
                if model.plan_version_id is not None and self._planning_repo is not None:
                    version = self._planning_repo.get_plan_version(user_id, model.plan_version_id)
                    if version is None:
                        raise AppError(
                            404,
                            "PLAN_VERSION_NOT_FOUND",
                            "Version de programme introuvable pour cet utilisateur.",
                        )
                return model.model_dump(mode="json")

            if action_type == AiActionType.batch_actions:
                model = BatchActionsProposalPayload.model_validate(raw_payload)
                normalized_steps: list[dict[str, Any]] = []
                for idx, step in enumerate(model.steps):
                    if not self._tool_registry.is_allowed_proposal_action(step.action_type.value):
                        raise AppError(
                            422,
                            "UNSUPPORTED_AI_ACTION",
                            f"L’action « {step.action_type.value} » n’est pas autorisée dans batch_actions.",
                        )
                    link_keys: set[str] = set()
                    if step.link_to_step:
                        for fk_name, src_idx in step.link_to_step.items():
                            if src_idx < 0 or src_idx >= idx:
                                raise AppError(
                                    422,
                                    "VALIDATION_ERROR",
                                    f"Référence inter-étapes invalide ({fk_name} -> étape {src_idx}) à l’étape {idx}.",
                                )
                            link_keys.add(fk_name)
                    step_payload = dict(step.payload or {})
                    for fk_name in link_keys:
                        step_payload.pop(fk_name, None)
                    validated_step_payload = self.validate_action_payload(
                        user_id,
                        step.action_type,
                        step_payload,
                        _skip_fks=link_keys,
                    )
                    normalized_steps.append(
                        {
                            "action_type": step.action_type.value,
                            "payload": validated_step_payload,
                            "link_to_step": dict(step.link_to_step) if step.link_to_step else None,
                        }
                    )
                return {
                    "summary": model.summary,
                    "steps": normalized_steps,
                    "compensate_on_failure": model.compensate_on_failure,
                }
        except ValidationError as exc:
            first_msg = exc.errors()[0].get("msg", "Paramètres d’action invalides.")
            raise AppError(422, "VALIDATION_ERROR", str(first_msg)) from exc

        raise AppError(422, "UNSUPPORTED_AI_ACTION", "Action IA non prise en charge.")
